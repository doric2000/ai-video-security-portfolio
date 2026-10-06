# Runtime config loading + threshold resolution.
# Comments in English.

import os
import json
import yaml
from datetime import datetime, time
from zoneinfo import ZoneInfo

def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_camera_context(camera_id: str, base_dir: str = "contexts") -> dict:
    path = os.path.join(base_dir, f"{camera_id}.yaml")
    if not os.path.exists(path):
        return {
            "camera_id": camera_id,
            "location_name": "Unknown",
            "environment_type": "unknown",
            "profile": "office_standard",
            "sensitivity": "medium",
            "notes": ""
        }
    return _load_yaml(path)

def load_profile(profile_name: str, base_dir: str = "profiles") -> dict:
    path = os.path.join(base_dir, f"{profile_name}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Profile not found: {path}")
    return _load_yaml(path)

def _parse_hhmm(v: str) -> time:
    hh, mm = v.split(":")
    return time(int(hh), int(mm))

def is_within_working_hours(profile: dict, now_utc: datetime) -> bool:
    wh = profile.get("working_hours", {}) or {}
    if not wh.get("enabled", False):
        return False

    tz = ZoneInfo(wh.get("timezone", "UTC"))
    now_local = now_utc.astimezone(tz)

    days = set(wh.get("days", []))
    # Python: Mon=0..Sun=6. We'll map to strings.
    map_day = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][now_local.weekday()]
    if days and map_day not in days:
        return False

    start = _parse_hhmm(wh.get("start", "00:00"))
    end = _parse_hhmm(wh.get("end", "23:59"))

    t = now_local.time()
    return (t >= start) and (t <= end)

def resolve_thresholds(context: dict, profile: dict) -> dict:
    sensitivity = (context.get("sensitivity") or "medium").lower()
    if sensitivity not in ("low","medium","high"):
        sensitivity = "medium"

    gd = profile.get("gating_defaults", {}) or {}
    loiter_map = gd.get("loitering_seconds_by_sensitivity", {}) or {}

    return {
        "min_confidence_person": float(gd.get("min_confidence_person", 0.75)),
        "loitering_seconds": int(loiter_map.get(sensitivity, loiter_map.get("medium", 30))),
        "restricted_zone_only": bool(profile.get("event_triggers", {}).get("restricted_zone_only", False)),
        "after_hours_presence": bool(profile.get("event_triggers", {}).get("after_hours_presence", False)),
        "loitering_enabled": bool(profile.get("event_triggers", {}).get("loitering", True)),
        "sensitivity": sensitivity,
    }

def should_open_candidate(event_meta: dict, context: dict, profile: dict, thresholds: dict) -> tuple[bool, str]:
    """
    Decide if this event should be sent to Ollama.
    Returns: (candidate_bool, reason_string)
    """
    label = (event_meta.get("label") or "").lower()
    if label != "person":
        return (False, "label_not_person")

    conf = float(event_meta.get("top_score", event_meta.get("score", 1.0)) or 1.0)
    if conf < thresholds["min_confidence_person"]:
        return (False, "low_confidence")

    now_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
    in_work_hours = is_within_working_hours(profile, now_utc)

    # If restricted-zone-only, require zone hit (if zones available).
    zones = event_meta.get("zones", []) or []
    if thresholds["restricted_zone_only"] and not zones:
        return (False, "restricted_zone_required_no_zone")

    # After-hours presence trigger
    if thresholds["after_hours_presence"] and not in_work_hours:
        return (True, "after_hours_presence")

    # Loitering trigger (requires duration)
    if thresholds["loitering_enabled"]:
        duration = float(event_meta.get("duration", 0.0) or 0.0)
        if duration >= thresholds["loitering_seconds"]:
            return (True, "loitering")

    return (False, "no_trigger")
