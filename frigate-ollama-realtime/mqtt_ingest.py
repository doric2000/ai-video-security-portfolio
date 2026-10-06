# MQTT ingest for Frigate (robust, JSON-only).
# - Subscribes to Frigate event/review topics (with wildcards).
# - Ignores binary snapshot topics.
# - Normalizes payload variants (after/before wrappers, review wrappers).
# - Aggregates updates by event id and triggers callback when event is closed (end_time present).

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Callable, Dict, Any, Optional, Tuple

import paho.mqtt.client as mqtt


@dataclass
class IngestConfig:
    host: str = "127.0.0.1"
    port: int = 1883
    topic_prefix: str = "frigate"
    username: str = ""
    password: str = ""
    keepalive: int = 60
    # If True, prints a short debug line for each JSON message.
    debug: bool = False
    # Evict active events not updated for this many seconds.
    stale_ttl_sec: int = 30 * 60


def _safe_json(payload: bytes) -> Optional[dict]:
    try:
        # Frigate JSON is utf-8; binary topics will fail here.
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None


def _should_ignore_topic(topic: str) -> bool:
    """
    Ignore binary/image topics and other noisy state topics.
    """
    t = topic.lower()
    # Binary snapshots often published like: frigate/<camera>/<label>/snapshot
    if "/snapshot" in t:
        return True
    # Optional: ignore frequent state topics to reduce noise
    if t.endswith("/state"):
        return True
    return False


def _unwrap_payload(msg: dict) -> dict:
    """
    Unwrap common Frigate wrappers:
    - { "after": {...}, "before": {...}, "type": ... }
    - { "payload": {...} }
    - { "review": {...} }
    """
    evt = msg

    if isinstance(evt, dict) and "after" in evt and isinstance(evt["after"], dict):
        evt = evt["after"]

    if isinstance(evt, dict) and "payload" in evt and isinstance(evt["payload"], dict):
        evt = evt["payload"]

    if isinstance(evt, dict) and "review" in evt and isinstance(evt["review"], dict):
        evt = evt["review"]

    return evt if isinstance(evt, dict) else {}


def _extract_event_fields(evt: dict) -> dict:
    """
    Best-effort extraction of an event-like object.
    Frigate may use different keys depending on topic/version.
    """
    event_id = (
        evt.get("id")
        or evt.get("event_id")
        or evt.get("eventId")
        or evt.get("review_id")
        or evt.get("reviewId")
    )

    camera = evt.get("camera") or evt.get("camera_id") or evt.get("cameraId")

    label = (
        evt.get("label")
        or evt.get("object")
        or evt.get("class")
        or evt.get("type")  # sometimes "type" describes the review kind
    )

    start_time = evt.get("start_time") or evt.get("startTime") or evt.get("start")
    end_time = evt.get("end_time") or evt.get("endTime") or evt.get("end")

    # zones may appear as zones / entered_zones
    zones = evt.get("zones") or evt.get("entered_zones") or evt.get("enteredZones") or []

    # confidence / score
    score = evt.get("top_score") or evt.get("score") or evt.get("confidence")

    # duration if possible
    duration = None
    try:
        if start_time is not None and end_time is not None:
            duration = float(end_time) - float(start_time)
    except Exception:
        duration = evt.get("duration")

    return {
        "id": event_id,
        "camera": camera,
        "label": label,
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration,
        "zones": zones,
        "top_score": score,
        "raw": evt,
    }


def _is_event_closed(event_meta: dict) -> bool:
    """
    We consider an event 'closed' when end_time is present (not None).
    """
    return event_meta.get("end_time") is not None


class FrigateMqttIngest:
    def __init__(
        self,
        config: IngestConfig,
        on_event_closed: Callable[[dict], None],
    ):
        self.cfg = config
        self.on_event_closed = on_event_closed

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if self.cfg.username:
            self.client.username_pw_set(self.cfg.username, self.cfg.password)

        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        # Active events aggregated by id
        self.active: Dict[str, dict] = {}
        self.last_seen: Dict[str, float] = {}

    def _subscribe_patterns(self) -> Tuple[str, ...]:
        """
        Subscribe to likely JSON topics for Frigate.
        We intentionally avoid subscribing to snapshot topics.
        """
        p = self.cfg.topic_prefix.rstrip("/")

        return (
            # Classic
            f"{p}/events",
            f"{p}/tracked_object_update",
            # Camera-scoped variants (some setups publish here)
            f"{p}/+/events",
            f"{p}/+/events/#",
            f"{p}/+/review",
            f"{p}/+/review/#",
            # Global review stream (in some versions)
            f"{p}/review",
            f"{p}/review/#",
            f"{p}/reviews",
            f"{p}/reviews/#",
        )

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        for t in self._subscribe_patterns():
            client.subscribe(t)

        if self.cfg.debug:
            print(f"[MQTT] connected rc={reason_code}, subscribed to patterns:")
            for t in self._subscribe_patterns():
                print(f"  - {t}")

    def _evict_stale(self):
        now = time.time()
        ttl = self.cfg.stale_ttl_sec
        stale_ids = [eid for eid, ts in self.last_seen.items() if (now - ts) > ttl]
        for eid in stale_ids:
            self.active.pop(eid, None)
            self.last_seen.pop(eid, None)

    def _merge_event(self, eid: str, incoming: dict) -> dict:
        prev = self.active.get(eid, {})
        merged = {**prev, **incoming}

        # Preserve zones if incoming has none
        if (not merged.get("zones")) and prev.get("zones"):
            merged["zones"] = prev["zones"]

        # Preserve label/camera if missing in incoming
        if (not merged.get("label")) and prev.get("label"):
            merged["label"] = prev["label"]
        if (not merged.get("camera")) and prev.get("camera"):
            merged["camera"] = prev["camera"]

        return merged

    def _on_message(self, client, userdata, msg):
        topic = msg.topic

        # Skip binary/noisy topics
        if _should_ignore_topic(topic):
            return

        data = _safe_json(msg.payload)
        if not data:
            # Not JSON => ignore (likely binary snapshot or other payload)
            return

        evt = _unwrap_payload(data)
        event_meta = _extract_event_fields(evt)

        eid = event_meta.get("id")
        if not eid:
            # If message has no id, it's not an event we can track.
            if self.cfg.debug:
                print(f"[MQTT] JSON without id on topic={topic} keys={list(evt.keys())[:12]}")
            return

        merged = self._merge_event(eid, event_meta)
        self.active[eid] = merged
        self.last_seen[eid] = time.time()

        if self.cfg.debug:
            cam = merged.get("camera")
            lbl = merged.get("label")
            et = merged.get("end_time")
            print(f"[MQTT] topic={topic} id={eid} camera={cam} label={lbl} end_time={et}")

        # Evict stale periodically
        if len(self.active) % 50 == 0:
            self._evict_stale()

        # Trigger only when closed
        if _is_event_closed(merged):
            try:
                self.on_event_closed(merged)
            finally:
                self.active.pop(eid, None)
                self.last_seen.pop(eid, None)

    def run_forever(self):
        self.client.connect(self.cfg.host, self.cfg.port, self.cfg.keepalive)
        self.client.loop_forever()
