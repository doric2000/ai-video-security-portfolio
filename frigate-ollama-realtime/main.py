# End-to-end pipeline runner (MQTT -> Gate -> Clip -> vLLM Video -> Decision).
# English comments only.

import os
import time
import yaml
from collections import deque
from datetime import datetime
from zoneinfo import ZoneInfo

from mqtt_ingest import FrigateMqttIngest, IngestConfig
from frigate_client import FrigateClient
from evidence import build_timeline, create_evidence_pack
from context_admin import start_context_admin
from ollama_analyzer import (
    analyze_clip_temporal_vllm,
    vision_describe_event,
    decide_event_json,
    analyze_clip_video_vllm,
)
from writers import append_jsonl, write_json, write_text

cfg = IngestConfig(
    host=os.environ.get("MQTT_HOST") or "127.0.0.1",
    port=int(os.environ.get("MQTT_PORT") or "1883"),
    topic_prefix=os.environ.get("MQTT_PREFIX") or "frigate",
    username=os.environ.get("MQTT_USER") or "",
    password=os.environ.get("MQTT_PASS") or "",
    debug=True,
)
# Base directory = project root (where main.py is located)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONTEXTS_DIR = os.path.join(BASE_DIR, "contexts")
PROFILES_DIR = os.path.join(BASE_DIR, "profiles")
WORK_DIR = os.path.join(BASE_DIR, "work")
OUT_DIR = os.path.join(BASE_DIR, "out")

DEBUG = os.environ.get("DEBUG") == "1"
MIN_CLIP_BYTES = int(os.environ.get("MIN_CLIP_BYTES", "51200"))
ALERT_MIN_SEVERITY = int(os.environ.get("ALERT_MIN_SEVERITY", "3"))
ALERT_MIN_CONFIDENCE = float(os.environ.get("ALERT_MIN_CONFIDENCE", "0.70"))
VISION_MAX_IMAGES = int(os.environ.get("VISION_MAX_IMAGES", "32"))
VIDEO_ANALYSIS_ENABLED = os.environ.get("VIDEO_ANALYSIS_ENABLED", "1") == "1"
VIDEO_FALLBACK_WINDOW_COUNT = int(os.environ.get("VIDEO_FALLBACK_WINDOW_COUNT", "4"))
VIDEO_MAX_IMAGES_PER_WINDOW = int(os.environ.get("VIDEO_MAX_IMAGES_PER_WINDOW", "8"))
VIDEO_FRAME_FALLBACK_ENABLED = os.environ.get("VIDEO_FRAME_FALLBACK_ENABLED", "0") == "1"
VIDEO_CLIP_MAX_SIZE_MB = int(os.environ.get("VIDEO_CLIP_MAX_SIZE_MB", "500"))
VIDEO_INCLUDE_TIMELINE_CONTEXT = os.environ.get("VIDEO_INCLUDE_TIMELINE_CONTEXT", "1") == "1"
# vLLM support (faster inference for large models)
USE_VLLM = os.environ.get("USE_VLLM", "1") == "1"
VLLM_HOST = os.environ.get("VLLM_HOST", "http://vllm:8000")  # Container DNS
VLLM_VIDEO_MODEL = os.environ.get("VLLM_VIDEO_MODEL", "Chunity/gemma-4-E4B-it-AWQ-4bit")
VLLM_TEXT_MODEL = os.environ.get("VLLM_TEXT_MODEL", VLLM_VIDEO_MODEL)
PROCESSED_MAX = int(os.environ.get("PROCESSED_MAX", "500"))
CONTEXT_ADMIN_ENABLED = os.environ.get("CONTEXT_ADMIN_ENABLED", "1") == "1"
CONTEXT_ADMIN_HOST = os.environ.get("CONTEXT_ADMIN_HOST", "0.0.0.0")
CONTEXT_ADMIN_PORT = int(os.environ.get("CONTEXT_ADMIN_PORT", "8080"))
FRIGATE_CONFIG_PATH = os.environ.get("FRIGATE_CONFIG_PATH", "/frigate-config/config.yaml")

_processed_ids = deque()
_processed_set = set()


def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_context(camera_id: str) -> dict:
    path = os.path.join(CONTEXTS_DIR, f"{camera_id}.yaml")
    if not os.path.exists(path):
        return {
            "camera_id": camera_id,
            "profile": "office_standard",
            "sensitivity": "medium",
            "camera_view": {"location_name": "Unknown", "description": ""},
            "working_hours": {"enabled": False},
        }
    return load_yaml(path)


def load_profile(profile_name: str) -> dict:
    path = os.path.join(PROFILES_DIR, f"{profile_name}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Profile not found: {path}")
    return load_yaml(path)


def within_working_hours(context: dict, ts: float | None = None) -> bool:
    wh = context.get("working_hours", {}) or {}
    if not wh.get("enabled", False):
        return False

    tz = ZoneInfo(wh.get("timezone", "UTC"))
    if ts is None:
        now_local = datetime.now(tz)
    else:
        now_local = datetime.fromtimestamp(float(ts), tz)

    days = set(wh.get("days", []))
    day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][now_local.weekday()]
    if days and day_name not in days:
        return False

    start_h, start_m = map(int, wh.get("start", "00:00").split(":"))
    end_h, end_m = map(int, wh.get("end", "23:59").split(":"))

    t = now_local.time()
    start_t = t.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
    end_t = t.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
    return (t >= start_t) and (t <= end_t)


def should_candidate(event_meta: dict, context: dict, profile: dict) -> tuple[bool, str]:
    """
    Simple scalable gate:
    - only person
    - confidence threshold
    - after-hours presence OR loitering
    """
    raw_label = event_meta.get("label")
    if raw_label is None:
        return False, "label_missing"
    label = (raw_label or "").lower()
    if label != "person":
        return False, "label_not_person"

    conf = float(event_meta.get("top_score") or 1.0)
    min_conf = float(profile.get("min_confidence_person", 0.75))
    if conf < min_conf:
        return False, "low_confidence"

    event_ts = event_meta.get("end_time") or event_meta.get("start_time")
    in_hours = within_working_hours(context, ts=float(event_ts) if event_ts else None)
    triggers = profile.get("triggers", {}) or {}

    sens = (context.get("sensitivity") or "medium").lower()
    loiter_map = profile.get("loitering_seconds_by_sensitivity", {}) or {}
    loiter_thr = int(loiter_map.get(sens, loiter_map.get("medium", 30)))

    duration = float(event_meta.get("duration") or 0.0)

    if triggers.get("after_hours_presence", False) and not in_hours:
        return True, "after_hours_presence"

    if triggers.get("loitering", True) and duration >= loiter_thr:
        return True, "loitering"

    return False, "no_trigger"


def resolve_alert_thresholds(context: dict) -> tuple[int, float]:
    notifications = context.get("notifications", {}) or {}
    min_severity = int(notifications.get("min_severity", ALERT_MIN_SEVERITY))
    min_confidence = float(notifications.get("min_confidence", ALERT_MIN_CONFIDENCE))
    return min_severity, min_confidence

def log(tag: str, msg: str) -> None:
    print(f"[{tag}] {msg}")


def _mark_processed(event_id: str) -> None:
    if event_id in _processed_set:
        return
    _processed_ids.append(event_id)
    _processed_set.add(event_id)
    while len(_processed_ids) > PROCESSED_MAX:
        oldest = _processed_ids.popleft()
        _processed_set.discard(oldest)


def _already_processed(event_id: str) -> bool:
    return event_id in _processed_set


def _download_clip_with_retry(frigate: FrigateClient, event_id: str, clip_path: str) -> bool:
    os.makedirs(os.path.dirname(clip_path), exist_ok=True)
    for attempt in range(2):
        if attempt > 0:
            time.sleep(1.0)
        try:
            log("CLIP", f"download_start event={event_id} attempt={attempt + 1}")
            frigate.download_event_clip(event_id, clip_path)
            size = os.path.getsize(clip_path)
            if size >= MIN_CLIP_BYTES:
                log("CLIP", f"download_ok event={event_id} bytes={size}")
                return True
            log("CLIP", f"too_small event={event_id} bytes={size}")
        except Exception as e:
            log("ERROR", f"clip_download_failed event={event_id} err={e}")
    log("CLIP", f"still_too_small event={event_id} -> skip")
    return False


def on_event_closed(event_meta: dict):
    camera_id = event_meta.get("camera")
    event_id = event_meta.get("id")
    if not camera_id or not event_id:
        return

    if _already_processed(event_id):
        log("PIPE", f"dup_skip camera={camera_id} event={event_id}")
        return

    _mark_processed(event_id)

    context = load_context(camera_id)
    profile_name = context.get("profile", "office_standard")
    profile = load_profile(profile_name)

    is_cand, gate_reason = should_candidate(event_meta, context, profile)
    in_hours = within_working_hours(context)
    if not is_cand:
        log("GATE", f"skip camera={camera_id} event={event_id} reason={gate_reason}")
        return

    log("PIPE", f"closed camera={camera_id} event={event_id}")
    log("HOURS", f"in_working_hours={in_hours} camera={camera_id} event={event_id}")
    log("GATE", f"pass camera={camera_id} event={event_id} reason={gate_reason}")

    frigate = FrigateClient(os.environ.get("FRIGATE_URL", "http://127.0.0.1:5000"))

    event_dir = os.path.join(WORK_DIR, str(event_id))
    os.makedirs(event_dir, exist_ok=True)
    clip_path = os.path.join(event_dir, "clip.mp4")

    if not _download_clip_with_retry(frigate, event_id, clip_path):
        return

    try:
        timeline = build_timeline(event_meta, context, profile, gate_reason)

        analysis_mode = "vision"
        video_model_used = None
        vision_text = ""
        frame_paths = []

        # Primary path: direct MP4 video analysis through vLLM.
        if VIDEO_ANALYSIS_ENABLED and USE_VLLM:
            clip_size_mb = os.path.getsize(clip_path) / (1024 * 1024)
            if clip_size_mb > VIDEO_CLIP_MAX_SIZE_MB:
                log("ERROR", f"video_too_large event={event_id} size_mb={clip_size_mb:.1f} limit_mb={VIDEO_CLIP_MAX_SIZE_MB}")
            else:
                log("AI", f"vllm_video_start event={event_id} model={VLLM_VIDEO_MODEL} size_mb={clip_size_mb:.1f}")
                try:
                    vision_text = analyze_clip_video_vllm(
                        clip_path=clip_path,
                        context=context,
                        vllm_host=VLLM_HOST,
                        model=VLLM_VIDEO_MODEL,
                        debug=DEBUG,
                        timeline=(timeline if VIDEO_INCLUDE_TIMELINE_CONTEXT else None),
                    )
                    if vision_text:
                        write_text(os.path.join(event_dir, "video_analysis.txt"), vision_text)
                        analysis_mode = "video"
                        video_model_used = f"{VLLM_VIDEO_MODEL} (vLLM video)"
                        log("AI", f"vllm_video_ok event={event_id}")
                    else:
                        log("AI", f"vllm_video_empty event={event_id}")
                except Exception as e:
                    log("ERROR", f"vllm_video_failed event={event_id} err={e}")
                    vision_text = ""
        elif VIDEO_ANALYSIS_ENABLED:
            log("AI", f"vllm_disabled event={event_id}")

        # Optional fallback: extract frames only when explicitly enabled.
        if not vision_text and VIDEO_FRAME_FALLBACK_ENABLED:
            log("EVID", f"frame_fallback_build_start event={event_id}")
            try:
                pack = create_evidence_pack(
                    clip_path=clip_path,
                    work_dir=WORK_DIR,
                    event_meta=event_meta,
                    context=context,
                    profile=profile,
                    gate_reason=gate_reason,
                )
                frame_paths = pack.frame_paths
                timeline = pack.timeline
                log("EVID", f"frame_fallback_build_ok event={event_id} frames={len(frame_paths)}")
            except Exception as e:
                log("ERROR", f"frame_fallback_build_failed event={event_id} err={e}")

            if frame_paths:
                try:
                    vision_text = analyze_clip_temporal_vllm(
                        frames=frame_paths,
                        context=context,
                        model=VLLM_VIDEO_MODEL,
                        vllm_host=VLLM_HOST,
                        debug=DEBUG,
                        window_count=VIDEO_FALLBACK_WINDOW_COUNT,
                        max_images_per_window=VIDEO_MAX_IMAGES_PER_WINDOW,
                    )
                    if vision_text:
                        write_text(os.path.join(event_dir, "temporal_analysis.txt"), vision_text)
                        analysis_mode = "temporal"
                        video_model_used = f"{VLLM_VIDEO_MODEL} (vLLM frames)"
                        log("AI", f"vllm_frame_fallback_ok event={event_id}")
                    else:
                        log("AI", f"vllm_frame_fallback_empty event={event_id}")
                except Exception as e:
                    log("ERROR", f"vllm_frame_fallback_failed event={event_id} err={e}")
                    vision_text = ""

        if not vision_text and VIDEO_FRAME_FALLBACK_ENABLED and frame_paths:
            log("AI", f"vision_start event={event_id}")
            try:
                vision_text = vision_describe_event(
                    frames=frame_paths,
                    context=context,
                    max_images=VISION_MAX_IMAGES,
                    model=VLLM_VIDEO_MODEL,
                    debug=DEBUG,
                )
                if vision_text:
                    write_text(os.path.join(event_dir, "vision.txt"), vision_text)
                    analysis_mode = "vision"
                    log("AI", f"vision_ok event={event_id}")
            except Exception as e:
                log("ERROR", f"vision_failed event={event_id} err={e}")
                vision_text = ""

        if not vision_text:
            log("ERROR", f"all_analysis_paths_failed event={event_id} -> skip decision")
            return

        log("AI", f"decide_start event={event_id}")
        try:
            decision = decide_event_json(
                vision_text=vision_text,
                timeline=timeline,
                context=context,
                profile=profile,
                in_working_hours=in_hours,
                event_dir=event_dir,
                model=VLLM_TEXT_MODEL,
                debug=DEBUG,
            )
        except Exception as e:
            # If the model did not return strict JSON, write a fallback decision
            log("ERROR", f"decision_parse_failed event={event_id} err={e}")
            # attempt to read any captured raw JSON/response saved by analyzer
            raw_path = os.path.join(event_dir, "decision_raw.json")
            raw_txt_path = os.path.join(event_dir, "decision_raw.txt")
            raw_contents = None
            try:
                if os.path.exists(raw_path):
                    with open(raw_path, "r", encoding="utf-8") as f:
                        raw_contents = f.read()
                elif os.path.exists(raw_txt_path):
                    with open(raw_txt_path, "r", encoding="utf-8") as f:
                        raw_contents = f.read()
            except Exception:
                raw_contents = None

            decision = {
                "is_event": False,
                "summary": (vision_text or "")[:400],
                "category": "ai_fallback",
                "severity": 1,
                "reason": "model_no_json",
                "confidence": 0.0,
            }
            # Save the fallback marker for inspection
            try:
                write_text(os.path.join(event_dir, "decision_fallback.txt"), raw_contents or "")
                write_json(os.path.join(event_dir, "decision.json"), decision, indent=2)
            except Exception:
                pass
        # The gate already applied per-camera/profile rules to decide this event is
        # worth recording. Don't let the AI override that with is_event=false.
        if gate_reason and not decision.get("is_event"):
            decision["is_event"] = True
            decision["severity"] = max(int(decision.get("severity") or 1), 2)
            log("GATE", f"gate_override event={event_id} reason={gate_reason}")

        write_json(os.path.join(event_dir, "decision.json"), decision, indent=2)
        log("AI", f"decide_ok event={event_id}")

        analysis = {
            "camera_id": camera_id,
            "event_id": event_id,
            "gate_reason": gate_reason,
            "in_working_hours": in_hours,
            "profile": profile_name,
            "analysis_mode": analysis_mode,
            "video_model": video_model_used,
            "timeline": timeline,
            "vision": vision_text,
            "decision": decision,
        }
        write_json(os.path.join(event_dir, "analysis.json"), analysis, indent=2)
        append_jsonl(os.path.join(OUT_DIR, "ai_events.jsonl"), analysis)
        log("DECISION", f"camera={camera_id} event={event_id} -> {decision.get('summary')}")

        decision_summary = decision.get("summary") or ""
        decision_category = decision.get("category") or "ai"
        decision_reason = decision.get("reason") or ""
        decision_confidence = float(decision.get("confidence", 0.0) or 0.0)

        event_description = "\n".join(
            line
            for line in [
                f"AI summary: {decision_summary}" if decision_summary else "AI summary: n/a",
                f"AI category: {decision_category}",
                f"AI severity: {decision.get('severity')}",
                f"AI confidence: {decision_confidence:.2f}",
                f"AI reason: {decision_reason}" if decision_reason else None,
            ]
            if line
        )

        try:
            frigate.set_event_description(event_id, event_description)
            log("FRIGATE", f"description_updated event={event_id}")
        except Exception as e:
            log("ERROR", f"description_update_failed event={event_id} err={e}")

        if decision.get("is_event") is True:
            try:
                frigate.set_event_sub_label(event_id, decision_category, decision_confidence)
                frigate.retain_event(event_id)
                log("FRIGATE", f"event_annotated event={event_id} sub_label={decision_category}")
            except Exception as e:
                log("ERROR", f"annotation_failed event={event_id} err={e}")

        alert_min_severity, alert_min_confidence = resolve_alert_thresholds(context)
        if (
            decision.get("is_event") is True
            and int(decision.get("severity", 0)) >= alert_min_severity
            and float(decision.get("confidence", 0.0)) >= alert_min_confidence
        ):
            alert = {
                "camera_id": camera_id,
                "event_id": event_id,
                "severity": decision.get("severity"),
                "confidence": decision.get("confidence"),
                "category": decision.get("category"),
                "summary": decision.get("summary"),
                "reason": decision.get("reason"),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            append_jsonl(os.path.join(OUT_DIR, "alerts.jsonl"), alert)
            log("ALERT", f"camera={camera_id} event={event_id} severity={alert['severity']}")
        else:
            log("ALERT", f"skip camera={camera_id} event={event_id}")

    except Exception as e:
        log("ERROR", f"analysis_failed event={event_id} err={e}")


if __name__ == "__main__":
    if CONTEXT_ADMIN_ENABLED:
        try:
            start_context_admin(
                CONTEXTS_DIR,
                CONTEXT_ADMIN_HOST,
                CONTEXT_ADMIN_PORT,
                OUT_DIR,
                WORK_DIR,
                FRIGATE_CONFIG_PATH,
                profiles_dir=PROFILES_DIR,
            )
        except Exception as e:
            log("ERROR", f"context_admin_failed err={e}")

    while True:
        try:
            ingest = FrigateMqttIngest(cfg, on_event_closed=on_event_closed)
            log("BOOT", "starting MQTT ingest loop")
            ingest.run_forever()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            log("ERROR", f"ingest_loop_failed err={e}")
            time.sleep(5)
