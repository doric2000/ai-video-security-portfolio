# Extracts evidence from a Frigate event clip.
# Comments in English.

import os
import json
import subprocess
from dataclasses import dataclass
from typing import List

@dataclass
class EvidencePack:
    clip_path: str
    frame_paths: List[str]
    timeline: dict

def _run(cmd: list) -> None:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{p.stderr}")

def _select_frames(frames: List[str], max_frames: int) -> List[str]:
    if len(frames) <= max_frames:
        return frames
    if max_frames <= 2:
        return [frames[0], frames[-1]][:max_frames]

    # Always include first and last, then sample evenly from start/middle/end.
    third = max(1, len(frames) // 3)
    segments = [
        (0, frames[:third]),
        (third, frames[third:2 * third]),
        (2 * third, frames[2 * third:]),
    ]
    per_segment = max(1, (max_frames - 2) // 3)
    picks = {0, len(frames) - 1}
    for offset, seg in segments:
        if not seg:
            continue
        step = max(1, int(round(len(seg) / float(per_segment))))
        for i in range(0, len(seg), step):
            picks.add(offset + i)
            if len(picks) >= max_frames:
                break
        if len(picks) >= max_frames:
            break

    # If still short, fill evenly across full set.
    if len(picks) < max_frames:
        step = max(1, int(round(len(frames) / float(max_frames))))
        for i in range(0, len(frames), step):
            picks.add(i)
            if len(picks) >= max_frames:
                break

    return [frames[i] for i in sorted(picks)[:max_frames]]


def extract_keyframes_ffmpeg(clip_path: str, out_dir: str, max_frames: int = 32) -> List[str]:
    """
    Practical keyframe strategy:
    - Use fps sampling to get representative frames across the clip.
    - For short clips, fps=2 yields enough coverage.
    """
    os.makedirs(out_dir, exist_ok=True)

    # 1) Get clip duration (best-effort)
    # If ffprobe is missing, fallback to fixed fps.
    fps = 2
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", clip_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if probe.returncode == 0:
            dur = float(probe.stdout.strip() or 0.0)
            # Choose fps so we get about max_frames frames.
            if dur > 0:
                fps = max(1, min(4, int(max_frames / max(dur, 1))))
    except Exception:
        pass

    # 2) Extract frames
    out_pattern = os.path.join(out_dir, "frame_%03d.jpg")
    _run([
        "ffmpeg", "-y", "-i", clip_path,
        "-vf", f"fps={fps},scale=896:-1",
        "-q:v", "3",
        out_pattern
    ])

    # 3) Ensure first/last are included and cap to max_frames
    frames = sorted([os.path.join(out_dir, f) for f in os.listdir(out_dir) if f.endswith(".jpg")])
    if not frames:
        return []
    return _select_frames(frames, max_frames)

def build_timeline(event_meta: dict, context: dict, profile: dict, gate_reason: str) -> dict:
    """
    Timeline is structured metadata (LLM-friendly).
    """
    return {
        "camera_id": event_meta.get("camera"),
        "event_id": event_meta.get("id"),
        "label": event_meta.get("label"),
        "start_time": event_meta.get("start_time"),
        "end_time": event_meta.get("end_time"),
        "duration_sec": event_meta.get("duration"),
        "zones": event_meta.get("zones", []),
        "top_score": event_meta.get("top_score", event_meta.get("score")),
        "gate_reason": gate_reason,
        "context_summary": {
            "location_name": context.get("camera_view", {}).get("location_name"),
            "profile": context.get("profile"),
            "sensitivity": context.get("sensitivity"),
        },
        "intent": context.get("security_intent", {}),
        "profile_defaults": profile,
    }

def create_evidence_pack(clip_path: str, work_dir: str, event_meta: dict, context: dict, profile: dict, gate_reason: str) -> EvidencePack:
    event_id = event_meta.get("id", "unknown")
    frames_dir = os.path.join(work_dir, str(event_id), "frames")
    frame_paths = extract_keyframes_ffmpeg(clip_path, frames_dir, max_frames=32)
    timeline = build_timeline(event_meta, context, profile, gate_reason)
    return EvidencePack(clip_path=clip_path, frame_paths=frame_paths, timeline=timeline)
