from __future__ import annotations

import base64
import html
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import requests
import yaml


CAMERA_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
SAFE_CAMERA_UPDATE_KEYS = {"detect", "objects", "zones", "record", "snapshots"}
SAFE_NEW_CAMERA_KEYS = {"enabled", "ffmpeg", "detect", "objects", "zones", "record", "snapshots"}
SAFE_TOP_OBJECT_KEYS = {"track"}
DEFAULT_TRACKED_OBJECTS = ["person"]
VLLM_HOST = os.environ.get("VLLM_HOST", "http://vllm:8000")
VLLM_TEXT_MODEL = os.environ.get("VLLM_TEXT_MODEL", "Chunity/gemma-4-E4B-it-AWQ-4bit")


def _safe_camera_id(camera_id: str) -> str:
    if not CAMERA_ID_RE.match(camera_id):
        raise ValueError("Invalid camera id")
    return camera_id


def _context_path(contexts_dir: str, camera_id: str) -> str:
    camera_id = _safe_camera_id(camera_id)
    return os.path.join(contexts_dir, f"{camera_id}.yaml")


def _list_camera_ids(contexts_dir: str) -> list[str]:
    if not os.path.isdir(contexts_dir):
        return []
    camera_ids = []
    for name in sorted(os.listdir(contexts_dir)):
        if not name.endswith((".yaml", ".yml")):
            continue
        camera_id = os.path.splitext(name)[0]
        if CAMERA_ID_RE.match(camera_id):
            camera_ids.append(camera_id)
    return camera_ids


def _read_context_text(contexts_dir: str, camera_id: str) -> str:
    path = _context_path(contexts_dir, camera_id)
    if not os.path.exists(path):
        return f"camera_id: {camera_id}\nprofile: office_standard\nsensitivity: medium\n"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_context_text(contexts_dir: str, camera_id: str, content: str) -> None:
    path = _context_path(contexts_dir, camera_id)
    parsed = yaml.safe_load(content) or {}
    if not isinstance(parsed, dict):
        raise ValueError("Context YAML must be a mapping")
    if parsed.get("camera_id") and parsed["camera_id"] != camera_id:
        raise ValueError("camera_id in YAML must match the selected camera")

    os.makedirs(contexts_dir, exist_ok=True)
    if os.path.exists(path):
        shutil.copy2(path, f"{path}.bak")
    fd, tmp_path = tempfile.mkstemp(prefix=f".{camera_id}.", suffix=".yaml", dir=contexts_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content.rstrip() + "\n")
        os.replace(tmp_path, path)
        os.chmod(path, 0o644)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _read_yaml_file(path: str) -> tuple[str, dict]:
    if not path:
        raise ValueError("Configuration path is not set")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    parsed = yaml.safe_load(content) or {}
    if not isinstance(parsed, dict):
        raise ValueError("Configuration YAML must be a mapping")
    return content, parsed


def _write_yaml_file(path: str, content: str) -> dict:
    if not path:
        raise ValueError("Configuration path is not set")
    parsed = yaml.safe_load(content) or {}
    if not isinstance(parsed, dict):
        raise ValueError("Configuration YAML must be a mapping")

    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    if os.path.exists(path):
        backup_path = f"{path}.bak"
        shutil.copy2(path, backup_path)

    fd, tmp_path = tempfile.mkstemp(prefix=".config.", suffix=".yaml", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content.rstrip() + "\n")
        os.replace(tmp_path, path)
        os.chmod(path, 0o644)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return parsed


def _dump_yaml(data: dict) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def _extract_json(txt: str) -> dict:
    start = txt.find("{")
    end = txt.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model did not return JSON")
    parsed = json.loads(txt[start:end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON must be an object")
    return parsed


def _message_text(response: object) -> str:
    if isinstance(response, list):
        return "\n".join(
            part.get("text", "")
            for part in response
            if isinstance(part, dict) and part.get("type") == "text"
        ).strip()
    return response.strip() if isinstance(response, str) else ""


def _read_context_dict(contexts_dir: str, camera_id: str) -> dict:
    text = _read_context_text(contexts_dir, camera_id)
    parsed = yaml.safe_load(text) or {}
    if not isinstance(parsed, dict):
        raise ValueError("Context YAML must be a mapping")
    return parsed


def _validate_rtsp_url(rtsp_url: str) -> str:
    rtsp_url = (rtsp_url or "").strip()
    parsed = urlparse(rtsp_url)
    if parsed.scheme not in ("rtsp", "rtsps"):
        raise ValueError("RTSP URL must start with rtsp:// or rtsps://")
    if not parsed.netloc:
        raise ValueError("RTSP URL must include a host")
    return rtsp_url


def _coerce_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _coerce_int(value: object, default: int, min_value: int, max_value: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(min_value, min(max_value, number))


def _coerce_float(value: object, default: float, min_value: float, max_value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(min_value, min(max_value, number))


def _list_from_answer(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _sanitize_points(points: object) -> list[list[float]]:
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError("Mask/zone drawings must contain at least three points")
    sanitized = []
    for point in points:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError("Drawing points must be [x, y] pairs")
        x = _coerce_float(point[0], 0.0, 0.0, 1.0)
        y = _coerce_float(point[1], 0.0, 0.0, 1.0)
        sanitized.append([round(x, 4), round(y, 4)])
    return sanitized


def _points_to_frigate(points: object) -> str:
    sanitized = _sanitize_points(points)
    return ",".join(f"{coord:.4f}".rstrip("0").rstrip(".") for point in sanitized for coord in point)


def _safe_name(value: object, fallback: str) -> str:
    name = str(value or "").strip().lower()
    name = re.sub(r"[^a-z0-9_]+", "_", name).strip("_")
    return name or fallback


def _default_context(camera_id: str, answers: dict) -> dict:
    wh = answers.get("working_hours") or {}
    location = str(answers.get("location_name") or "Camera Area").strip()
    normal = _list_from_answer(answers.get("normal_activity"))
    risks = _list_from_answer(answers.get("risks_to_monitor"))
    notifications = answers.get("notifications") or {}
    chosen_profile = str(answers.get("profile") or "").strip() or "office_standard"
    return {
        "camera_id": camera_id,
        "profile": chosen_profile,
        "sensitivity": str(answers.get("sensitivity") or "medium").strip().lower(),
        "camera_view": {
            "location_name": location,
            "description": str(answers.get("camera_description") or f"Camera monitoring {location}.").strip(),
        },
        "areas_of_interest": [
            {"name": "Primary Area", "intent": str(answers.get("monitoring_goal") or "Monitor important security activity.").strip()}
        ],
        "security_intent": {
            "primary_risks": risks or ["after_hours_presence", "loitering"],
            "what_is_normal": normal or ["Routine authorized activity during working hours."],
            "what_is_suspicious": risks or ["After-hours presence", "Loitering", "Unauthorized handling of equipment"],
        },
        "notifications": {
            "min_severity": _coerce_int(notifications.get("min_severity"), 3, 1, 5),
            "min_confidence": _coerce_float(notifications.get("min_confidence"), 0.7, 0.0, 1.0),
        },
        "working_hours": {
            "enabled": _coerce_bool(wh.get("enabled"), True),
            "timezone": str(wh.get("timezone") or "Asia/Jerusalem"),
            "days": _list_from_answer(wh.get("days")) or ["Sun", "Mon", "Tue", "Wed", "Thu"],
            "start": str(wh.get("start") or "09:00"),
            "end": str(wh.get("end") or "17:00"),
        },
    }


def _drawings_to_camera_config(drawings: dict, tracked_objects: list[str]) -> dict:
    updates: dict = {}
    mask_values = []
    for index, mask in enumerate((drawings or {}).get("masks") or []):
        mask_values.append(_points_to_frigate(mask.get("points")))
    if mask_values:
        updates.setdefault("objects", {}).setdefault("filters", {}).setdefault("person", {})["mask"] = mask_values

    zones = {}
    for index, zone in enumerate((drawings or {}).get("zones") or []):
        zone_name = _safe_name(zone.get("name"), f"zone_{index + 1}")
        zones[zone_name] = {
            "coordinates": _points_to_frigate(zone.get("points")),
            "objects": tracked_objects or DEFAULT_TRACKED_OBJECTS,
        }
    if zones:
        updates["zones"] = zones
    return updates


def _build_safe_config(current: dict, mode: str, camera_id: str, rtsp_url: str, answers: dict, drawings: dict) -> tuple[dict, dict]:
    proposed = deepcopy(current)
    proposed.setdefault("cameras", {})
    camera_exists = camera_id in proposed["cameras"]
    if mode == "existing" and not camera_exists:
        raise ValueError(f"Camera does not exist in Frigate config: {camera_id}")
    if mode == "new" and camera_exists:
        raise ValueError(f"Camera already exists in Frigate config: {camera_id}")

    tracked_objects = _list_from_answer(answers.get("tracked_objects")) or deepcopy(proposed.get("objects", {}).get("track") or DEFAULT_TRACKED_OBJECTS)
    proposed.setdefault("objects", {})["track"] = tracked_objects

    detect = answers.get("detect") or {}
    detect_cfg = {
        "enabled": _coerce_bool(detect.get("enabled"), True),
        "width": _coerce_int(detect.get("width"), 896, 320, 4096),
        "height": _coerce_int(detect.get("height"), 512, 240, 2160),
        "fps": _coerce_int(detect.get("fps"), 5, 1, 30),
    }
    recording = answers.get("recording") or {}
    record_cfg = {
        "enabled": _coerce_bool(recording.get("enabled"), True),
        "retain": {
            "days": _coerce_int(recording.get("retain_days"), 7, 1, 365),
            "mode": "motion",
        },
    }
    snapshots_cfg = {"enabled": True, "retain": {"default": 7}}
    camera_updates = {
        "detect": detect_cfg,
        "record": record_cfg,
        "snapshots": snapshots_cfg,
    }
    camera_updates.update(_drawings_to_camera_config(drawings or {}, tracked_objects))

    if mode == "new":
        rtsp_url = _validate_rtsp_url(rtsp_url)
        camera_cfg = {
            "enabled": True,
            "ffmpeg": {
                "inputs": [
                    {
                        "path": rtsp_url,
                        "roles": ["detect", "record"],
                    }
                ]
            },
        }
        camera_cfg.update(camera_updates)
        proposed["cameras"][camera_id] = camera_cfg
    else:
        existing = deepcopy(proposed["cameras"].get(camera_id) or {})
        existing.update(camera_updates)
        # If a new RTSP URL was submitted, update only the ffmpeg path (targeted, not a full ffmpeg replace)
        submitted_rtsp = (rtsp_url or "").strip()
        if submitted_rtsp:
            ff = existing.setdefault("ffmpeg", {})
            ff_inputs = ff.setdefault("inputs", [{}])
            if not ff_inputs:
                ff_inputs.append({})
            ff_inputs[0]["path"] = submitted_rtsp
        proposed["cameras"][camera_id] = existing

    patch = {
        "objects": {"track": tracked_objects},
        "cameras": {camera_id: camera_updates if mode == "existing" else proposed["cameras"][camera_id]},
    }
    return proposed, patch


def _strip_safe_updates_for_compare(config: dict, camera_id: str, is_new: bool) -> dict:
    stripped = deepcopy(config)
    objects = stripped.get("objects")
    if isinstance(objects, dict):
        for key in SAFE_TOP_OBJECT_KEYS:
            objects.pop(key, None)
        if not objects:
            stripped.pop("objects", None)

    cameras = stripped.get("cameras")
    if isinstance(cameras, dict):
        if is_new:
            cameras.pop(camera_id, None)
        else:
            camera_cfg = cameras.get(camera_id)
            if isinstance(camera_cfg, dict):
                for key in SAFE_CAMERA_UPDATE_KEYS:
                    camera_cfg.pop(key, None)
        if not cameras:
            stripped.pop("cameras", None)
    return stripped


def _validate_safe_config_update(current: dict, proposed: dict, camera_id: str) -> None:
    if not isinstance(proposed, dict):
        raise ValueError("Frigate config must be an object")
    if "cameras" not in proposed or not isinstance(proposed["cameras"], dict):
        raise ValueError("Frigate config must include cameras mapping")
    current_cameras = current.get("cameras") or {}
    proposed_cameras = proposed.get("cameras") or {}
    is_new = camera_id not in current_cameras
    if camera_id not in proposed_cameras:
        raise ValueError("Proposed Frigate config is missing selected camera")

    if _strip_safe_updates_for_compare(current, camera_id, is_new) != _strip_safe_updates_for_compare(proposed, camera_id, is_new):
        raise ValueError("Frigate config changes include fields outside the safe setup subset")

    if is_new:
        camera_cfg = proposed_cameras.get(camera_id) or {}
        extra = set(camera_cfg) - SAFE_NEW_CAMERA_KEYS
        if extra:
            raise ValueError(f"New camera config includes unsupported keys: {sorted(extra)}")


SETUP_LLM_ENABLED = os.environ.get("SETUP_LLM_ENABLED", "0") == "1"


def _call_setup_llm(draft: dict) -> dict:
    """
    Build the setup proposal. The form already produces all the YAML we need,
    so by default we return the draft unchanged. Set SETUP_LLM_ENABLED=1 to
    enable an experimental vLLM rewrite of the camera_context wording.
    """
    def _fallback() -> dict:
        return {
            "camera_context": draft.get("camera_context") or {},
            "frigate_patch": draft.get("frigate_patch") or {},
            "summary": "Ready to save.",
            "warnings": draft.get("warnings") or ["Restart Frigate after saving to apply stream and detector changes."],
        }

    if not SETUP_LLM_ENABLED:
        return _fallback()

    system_msg = (
        "You generate strict JSON for a security camera setup wizard. "
        "Return JSON only. Keep Frigate changes inside the provided safe draft. "
        "Do not include markdown."
    )
    user_msg = (
        "Create a camera setup proposal from this draft. "
        "Improve the camera_context wording for security operators. "
        "Return exactly these top-level keys: camera_context, frigate_patch, summary, warnings.\n\n"
        f"DRAFT:\n{json.dumps(draft, ensure_ascii=False, indent=2)}"
    )
    payload = {
        "model": VLLM_TEXT_MODEL,
        "messages": [
            {"role": "system", "content": [{"type": "text", "text": system_msg}]},
            {"role": "user", "content": [{"type": "text", "text": user_msg}]},
        ],
        "temperature": 0.0,
        "max_tokens": 2048,
    }
    url = VLLM_HOST.rstrip("/") + "/v1/chat/completions"
    try:
        response = requests.post(url, json=payload, timeout=300)
    except Exception as e:
        print(f"[SETUP] vLLM unreachable, using fallback: {e}")
        return _fallback()

    if not response.ok:
        print(f"[SETUP] vLLM returned {response.status_code}, using fallback: {response.text[:200]}")
        return _fallback()

    try:
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        text = _message_text(content)
        if not text:
            return _fallback()
        parsed = _extract_json(text)
        for key in ("camera_context", "frigate_patch", "summary", "warnings"):
            if key not in parsed:
                parsed[key] = _fallback()[key]
        if not isinstance(parsed["camera_context"], dict):
            parsed["camera_context"] = draft.get("camera_context") or {}
        if not isinstance(parsed["frigate_patch"], dict):
            parsed["frigate_patch"] = draft.get("frigate_patch") or {}
        if not isinstance(parsed["warnings"], list):
            parsed["warnings"] = [str(parsed["warnings"])]
        parsed["summary"] = str(parsed["summary"] or "Generated setup proposal.")
        parsed["warnings"] = [str(item) for item in parsed["warnings"] if str(item).strip()]
        return parsed
    except Exception as e:
        print(f"[SETUP] vLLM response parse failed, using fallback: {e}")
        return _fallback()


def _page(camera_id: str, content: str, cameras: list[str], message: str = "", error: str = "") -> str:
    camera_options = "\n".join(
        f'<option value="{html.escape(c)}" {"selected" if c == camera_id else ""}>{html.escape(c)}</option>'
        for c in cameras
    )
    status = ""
    if message:
        status = f'<div class="status ok">{html.escape(message)}</div>'
    if error:
        status = f'<div class="status error">{html.escape(error)}</div>'

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Context</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #101214;
      --panel: #171b1f;
      --text: #edf0f2;
      --muted: #a6adb4;
      --line: #2b3238;
      --accent: #5fb3ff;
      --ok: #52c16a;
      --err: #ff6b6b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.4 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 14px 18px;
      border-bottom: 1px solid var(--line);
      background: #12161a;
    }}
    h1 {{
      margin: 0;
      font-size: 18px;
      font-weight: 650;
    }}
    main {{
      width: min(1180px, 100%);
      margin: 0 auto;
      padding: 18px;
    }}
    form.toolbar {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 12px;
    }}
    select, button {{
      height: 36px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      color: var(--text);
      padding: 0 10px;
      font: inherit;
    }}
    button {{
      background: var(--accent);
      border-color: var(--accent);
      color: #06121d;
      font-weight: 650;
      cursor: pointer;
    }}
    textarea {{
      width: 100%;
      min-height: calc(100vh - 170px);
      resize: vertical;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      color: var(--text);
      font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      tab-size: 2;
    }}
    .status {{
      margin-bottom: 12px;
      padding: 9px 11px;
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    .ok {{ border-color: color-mix(in srgb, var(--ok) 45%, var(--line)); color: var(--ok); }}
    .error {{ border-color: color-mix(in srgb, var(--err) 45%, var(--line)); color: var(--err); }}
    .spacer {{ flex: 1; }}
    .muted {{ color: var(--muted); }}
  </style>
</head>
<body>
  <header>
    <h1>AI Context</h1>
    <span class="muted">{html.escape(camera_id)}.yaml</span>
  </header>
  <main>
    {status}
    <form class="toolbar" method="get" action="/context">
      <select name="camera" onchange="this.form.submit()">
        {camera_options}
      </select>
      <div class="spacer"></div>
    </form>
    <form method="post" action="/context?camera={html.escape(camera_id)}">
      <textarea name="content" spellcheck="false">{html.escape(content)}</textarea>
      <div class="toolbar" style="margin-top: 12px;">
        <button type="submit">Save</button>
      </div>
    </form>
  </main>
</body>
</html>
"""


class ContextAdminHandler(BaseHTTPRequestHandler):
    contexts_dir = "contexts"
    profiles_dir = "profiles"
    out_dir = "out"
    work_dir = "work"
    frigate_config_path = ""

    def log_message(self, fmt: str, *args) -> None:
        print(f"[CONTEXT_ADMIN] {self.address_string()} {fmt % args}")

    def _send(self, status: int, body: str, content_type: str = "text/html; charset=utf-8") -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, status: int, payload: object) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False), "application/json; charset=utf-8")

    def _read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return json.loads(raw or "{}")
        form = parse_qs(raw, keep_blank_values=True)
        return {k: v[0] if v else "" for k, v in form.items()}

    def _read_jsonl(self, name: str, limit: int) -> list[dict]:
        path = os.path.join(self.out_dir, name)
        if not os.path.exists(path):
            return []
        rows = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return list(reversed(rows[-limit:]))

    def _all_camera_ids(self) -> list[str]:
        camera_ids = set(_list_camera_ids(self.contexts_dir))
        try:
            _, config = _read_yaml_file(self.frigate_config_path)
            for camera_id in (config.get("cameras") or {}).keys():
                if CAMERA_ID_RE.match(str(camera_id)):
                    camera_ids.add(str(camera_id))
        except Exception:
            pass
        return sorted(camera_ids)

    def _handle_setup_defaults(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        camera_id = _safe_camera_id((query.get("camera") or ["front_door"])[0])
        context_text = _read_context_text(self.contexts_dir, camera_id)
        context_yaml = yaml.safe_load(context_text) or {}
        if not isinstance(context_yaml, dict):
            context_yaml = {}
        _, frigate_config = _read_yaml_file(self.frigate_config_path)
        camera_config = (frigate_config.get("cameras") or {}).get(camera_id, {})
        objects = frigate_config.get("objects") or {}
        _ff_inputs = ((camera_config or {}).get("ffmpeg") or {}).get("inputs") or []
        _rtsp_url = _ff_inputs[0].get("path", "") if _ff_inputs else ""
        self._send_json(200, {
            "camera_id": camera_id,
            "cameras": self._all_camera_ids(),
            "context": context_yaml if isinstance(context_yaml, dict) else {},
            "context_content": context_text,
            "frigate_camera": camera_config if isinstance(camera_config, dict) else {},
            "rtsp_url": _rtsp_url,
            "tracked_objects": objects.get("track") or DEFAULT_TRACKED_OBJECTS,
            "defaults": {
                "timezone": "Asia/Jerusalem",
                "working_days": ["Sun", "Mon", "Tue", "Wed", "Thu"],
                "working_start": "09:00",
                "working_end": "17:00",
                "detect": {
                    "width": ((camera_config or {}).get("detect") or {}).get("width", 896),
                    "height": ((camera_config or {}).get("detect") or {}).get("height", 512),
                    "fps": ((camera_config or {}).get("detect") or {}).get("fps", 5),
                },
                "recording": {
                    "enabled": ((camera_config or {}).get("record") or {}).get("enabled", True),
                    "retain_days": (((camera_config or {}).get("record") or {}).get("retain") or {}).get("days", 7),
                },
                "notifications": {
                    "min_severity": ((context_yaml or {}).get("notifications") or {}).get("min_severity", 3),
                    "min_confidence": ((context_yaml or {}).get("notifications") or {}).get("min_confidence", 0.7),
                },
            },
            "profiles": self._list_profiles(),
        })

    def _handle_setup_propose(self) -> None:
        payload = self._read_json_body()
        mode = str(payload.get("mode") or "existing").strip().lower()
        if mode not in ("existing", "new"):
            raise ValueError("mode must be existing or new")
        camera_id = _safe_camera_id(str(payload.get("camera_id") or ""))
        rtsp_url = str(payload.get("rtsp_url") or "")
        answers = payload.get("answers") or {}
        drawings = payload.get("drawings") or {}
        if not isinstance(answers, dict) or not isinstance(drawings, dict):
            raise ValueError("answers and drawings must be objects")

        _, current_config = _read_yaml_file(self.frigate_config_path)
        camera_context = _default_context(camera_id, answers)
        frigate_config, frigate_patch = _build_safe_config(current_config, mode, camera_id, rtsp_url, answers, drawings)
        draft = {
            "mode": mode,
            "camera_id": camera_id,
            "answers": answers,
            "drawings": drawings,
            "camera_context": camera_context,
            "frigate_patch": frigate_patch,
            "summary": "Generated camera setup proposal.",
            "warnings": ["Restart Frigate after saving to apply stream and detector changes."],
        }
        proposal = _call_setup_llm(draft)
        proposed_context = proposal.get("camera_context") or {}
        if not isinstance(proposed_context, dict):
            raise ValueError("camera_context must be an object")
        proposed_context["camera_id"] = camera_id
        warnings = proposal.get("warnings") or []
        if "Restart Frigate after saving to apply stream and detector changes." not in warnings:
            warnings.append("Restart Frigate after saving to apply stream and detector changes.")

        _validate_safe_config_update(current_config, frigate_config, camera_id)
        self._send_json(200, {
            "ok": True,
            "camera_id": camera_id,
            "mode": mode,
            "camera_context": proposed_context,
            "camera_context_yaml": _dump_yaml(proposed_context),
            "frigate_patch": frigate_patch,
            "frigate_config": frigate_config,
            "frigate_config_yaml": _dump_yaml(frigate_config),
            "summary": proposal.get("summary") or "Generated setup proposal.",
            "warnings": warnings,
            "llm_model": VLLM_TEXT_MODEL,
        })

    def _handle_setup_apply(self) -> None:
        payload = self._read_json_body()
        camera_id = _safe_camera_id(str(payload.get("camera_id") or ""))
        camera_context = payload.get("camera_context") or {}
        frigate_config = payload.get("frigate_config") or {}
        if not isinstance(camera_context, dict):
            raise ValueError("camera_context must be an object")
        if not isinstance(frigate_config, dict):
            raise ValueError("frigate_config must be an object")
        camera_context["camera_id"] = camera_id

        _, current_config = _read_yaml_file(self.frigate_config_path)
        _validate_safe_config_update(current_config, frigate_config, camera_id)
        context_content = _dump_yaml(camera_context)
        frigate_content = _dump_yaml(frigate_config)
        _write_context_text(self.contexts_dir, camera_id, context_content)
        parsed_frigate = _write_yaml_file(self.frigate_config_path, frigate_content)
        self._send_json(200, {
            "ok": True,
            "camera_id": camera_id,
            "context": camera_context,
            "frigate_config": parsed_frigate,
            "message": "Saved. Restart Frigate to apply service-level changes.",
        })

    def _handle_setup_delete(self) -> None:
        payload = self._read_json_body()
        camera_id = _safe_camera_id(str(payload.get("camera_id") or ""))

        _, current_config = _read_yaml_file(self.frigate_config_path)
        cameras = (current_config.get("cameras") or {}) if isinstance(current_config, dict) else {}
        context_path = _context_path(self.contexts_dir, camera_id)
        in_frigate = camera_id in cameras
        on_disk = os.path.exists(context_path)
        if not in_frigate and not on_disk:
            self._send_json(404, {"ok": False, "error": f"Camera '{camera_id}' not found"})
            return

        new_config = deepcopy(current_config) if isinstance(current_config, dict) else {}
        if in_frigate:
            del new_config["cameras"][camera_id]
        parsed_frigate = _write_yaml_file(self.frigate_config_path, _dump_yaml(new_config))

        if on_disk:
            try:
                os.remove(context_path)
            except Exception as e:
                self._send_json(500, {"ok": False, "error": f"Removed Frigate stanza but failed to delete context: {e}"})
                return

        self._send_json(200, {
            "ok": True,
            "removed_camera_id": camera_id,
            "frigate_config": parsed_frigate,
            "message": f"Removed camera '{camera_id}'. Restart Frigate to release the stream.",
        })

    def _list_profiles(self) -> list[dict]:
        profiles_dir = self.profiles_dir
        if not os.path.isdir(profiles_dir):
            return []
        out: list[dict] = []
        for name in sorted(os.listdir(profiles_dir)):
            if not name.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(profiles_dir, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            profile_name = str(data.get("profile_name") or os.path.splitext(name)[0])
            out.append({
                "name": profile_name,
                "display_name": str(data.get("display_name") or profile_name),
                "description": str(data.get("description") or "").strip(),
                "working_hours_required": bool(data.get("working_hours_enabled", False)),
                "triggers": data.get("triggers") or {},
            })
        return out

    def _handle_rtsp_probe(self) -> None:
        payload = self._read_json_body()
        rtsp_url = str(payload.get("rtsp_url") or "").strip()
        if not rtsp_url:
            raise ValueError("rtsp_url is required")
        if not (rtsp_url.startswith("rtsp://") or rtsp_url.startswith("rtsps://")):
            self._send_json(200, {"ok": False, "error": "URL must start with rtsp:// or rtsps://"})
            return

        probe_cmd = [
            "ffprobe", "-v", "error",
            "-rtsp_transport", "tcp",
            "-show_streams", "-of", "json",
            "-timeout", "5000000",
            rtsp_url,
        ]
        try:
            probe = subprocess.run(probe_cmd, capture_output=True, timeout=12)
        except FileNotFoundError:
            self._send_json(200, {"ok": False, "error": "ffprobe not installed in worker container"})
            return
        except subprocess.TimeoutExpired:
            self._send_json(200, {"ok": False, "error": "Connection timed out after 12s"})
            return

        if probe.returncode != 0:
            err = (probe.stderr or b"").decode("utf-8", errors="replace").strip().splitlines()
            msg = err[-1] if err else "ffprobe failed"
            self._send_json(200, {"ok": False, "error": msg})
            return

        codec = ""
        width = 0
        height = 0
        try:
            info = json.loads(probe.stdout or b"{}")
            for stream in info.get("streams", []) or []:
                if stream.get("codec_type") == "video":
                    codec = str(stream.get("codec_name") or "")
                    width = int(stream.get("width") or 0)
                    height = int(stream.get("height") or 0)
                    break
        except Exception:
            pass

        snapshot_b64 = ""
        snapshot_cmd = [
            "ffmpeg", "-v", "error",
            "-rtsp_transport", "tcp",
            "-i", rtsp_url,
            "-frames:v", "1",
            "-f", "mjpeg", "pipe:1",
        ]
        try:
            snap = subprocess.run(snapshot_cmd, capture_output=True, timeout=12)
            if snap.returncode == 0 and snap.stdout:
                snapshot_b64 = base64.b64encode(snap.stdout).decode("ascii")
        except Exception:
            snapshot_b64 = ""

        self._send_json(200, {
            "ok": True,
            "codec": codec,
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}" if width and height else "",
            "snapshot_b64": snapshot_b64,
        })

    def _handle_api_get(self, parsed) -> bool:
        if parsed.path == "/api/cameras":
            self._send_json(200, {"cameras": self._all_camera_ids()})
            return True

        if parsed.path == "/api/profiles":
            self._send_json(200, {"profiles": self._list_profiles()})
            return True

        if parsed.path == "/api/setup/defaults":
            self._handle_setup_defaults()
            return True

        if parsed.path == "/api/context":
            camera_id = self._camera_from_query()
            content = _read_context_text(self.contexts_dir, camera_id)
            parsed_yaml = yaml.safe_load(content) or {}
            self._send_json(200, {"camera_id": camera_id, "content": content, "parsed": parsed_yaml})
            return True

        if parsed.path == "/api/frigate-config":
            content, parsed_yaml = _read_yaml_file(self.frigate_config_path)
            self._send_json(200, {"content": content, "parsed": parsed_yaml})
            return True

        if parsed.path == "/api/ai/events":
            query = parse_qs(parsed.query)
            limit = int((query.get("limit") or ["50"])[0])
            camera = (query.get("camera") or [""])[0] or None
            events = self._read_jsonl("ai_events.jsonl", 500)
            if camera:
                events = [e for e in events if e.get("camera_id") == camera]
            self._send_json(200, {"events": events[:max(1, min(limit, 500))]})
            return True

        if parsed.path == "/api/ai/alerts":
            query = parse_qs(parsed.query)
            limit = int((query.get("limit") or ["50"])[0])
            self._send_json(200, {"alerts": self._read_jsonl("alerts.jsonl", max(1, min(limit, 500)))})
            return True

        return False

    def _camera_from_query(self) -> str:
        query = parse_qs(urlparse(self.path).query)
        camera = (query.get("camera") or [""])[0]
        cameras = self._all_camera_ids()
        if not camera:
            camera = cameras[0] if cameras else "front_door"
        return _safe_camera_id(camera)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"ok": True})
            return
        try:
            if self._handle_api_get(parsed):
                return
        except Exception as e:
            self._send_json(400, {"error": str(e)})
            return
        if parsed.path not in ("/", "/context"):
            self._send(404, "Not found", "text/plain; charset=utf-8")
            return
        try:
            camera_id = self._camera_from_query()
            cameras = _list_camera_ids(self.contexts_dir)
            if camera_id not in cameras:
                cameras.append(camera_id)
            content = _read_context_text(self.contexts_dir, camera_id)
            self._send(200, _page(camera_id, content, cameras))
        except Exception as e:
            self._send(400, _page("front_door", "", _list_camera_ids(self.contexts_dir), error=str(e)))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/context":
            try:
                camera_id = self._camera_from_query()
                payload = self._read_json_body()
                content = str(payload.get("content") or "")
                _write_context_text(self.contexts_dir, camera_id, content)
                parsed_yaml = yaml.safe_load(content) or {}
                self._send_json(200, {"ok": True, "camera_id": camera_id, "content": content, "parsed": parsed_yaml})
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        if parsed.path == "/api/frigate-config":
            try:
                payload = self._read_json_body()
                content = str(payload.get("content") or "")
                parsed_yaml = _write_yaml_file(self.frigate_config_path, content)
                self._send_json(200, {"ok": True, "content": content, "parsed": parsed_yaml})
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        if parsed.path == "/api/rtsp-probe":
            try:
                self._handle_rtsp_probe()
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        if parsed.path == "/api/setup/propose":
            try:
                self._handle_setup_propose()
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        if parsed.path == "/api/setup/apply":
            try:
                self._handle_setup_apply()
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        if parsed.path == "/api/setup/delete":
            try:
                self._handle_setup_delete()
            except Exception as e:
                self._send_json(400, {"ok": False, "error": str(e)})
            return

        if parsed.path != "/context":
            self._send(404, "Not found", "text/plain; charset=utf-8")
            return
        try:
            camera_id = self._camera_from_query()
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length).decode("utf-8")
            form = parse_qs(raw, keep_blank_values=True)
            content = (form.get("content") or [""])[0]
            _write_context_text(self.contexts_dir, camera_id, content)
            cameras = _list_camera_ids(self.contexts_dir)
            self._send(200, _page(camera_id, content, cameras, message="Saved"))
        except Exception as e:
            cameras = _list_camera_ids(self.contexts_dir)
            camera_id = "front_door"
            try:
                camera_id = self._camera_from_query()
            except Exception:
                pass
            content = ""
            try:
                content = _read_context_text(self.contexts_dir, camera_id)
            except Exception:
                pass
            self._send(400, _page(camera_id, content, cameras, error=str(e)))


def start_context_admin(
    contexts_dir: str,
    host: str = "0.0.0.0",
    port: int = 8080,
    out_dir: str = "out",
    work_dir: str = "work",
    frigate_config_path: str = "",
    profiles_dir: str = "profiles",
) -> threading.Thread:
    handler = type(
        "ConfiguredContextAdminHandler",
        (ContextAdminHandler,),
        {
            "contexts_dir": contexts_dir,
            "profiles_dir": profiles_dir,
            "out_dir": out_dir,
            "work_dir": work_dir,
            "frigate_config_path": frigate_config_path,
        },
    )
    server = ThreadingHTTPServer((host, port), handler)
    thread = threading.Thread(target=server.serve_forever, name="context-admin", daemon=True)
    thread.start()
    print(f"[CONTEXT_ADMIN] listening on {host}:{port}")
    return thread
