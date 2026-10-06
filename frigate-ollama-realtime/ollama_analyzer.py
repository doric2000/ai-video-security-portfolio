# Ollama multi-step analysis: Vision description -> Final JSON decision.
# Comments in English.

import base64
import json
import os
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/") + "/api/generate"
VLLM_HOST = os.environ.get("VLLM_HOST", "http://vllm:8000")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

REQUIRED_DECISION_KEYS = {
    "is_event",
    "summary",
    "category",
    "severity",
    "confidence",
    "reason",
}

def _b64_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _load_prompt(path: str, fallback: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return fallback.strip()


def _message_text(response: object) -> str:
    if isinstance(response, list):
        return "\n".join(
            part.get("text", "")
            for part in response
            if isinstance(part, dict) and part.get("type") == "text"
        ).strip()
    return (response or "").strip() if isinstance(response, str) else ""


def _select_frames(frames: List[str], max_images: int) -> List[str]:
    if len(frames) <= max_images:
        return frames
    if max_images <= 2:
        return [frames[0], frames[-1]][:max_images]

    third = max(1, len(frames) // 3)
    segments = [
        (0, frames[:third]),
        (third, frames[third:2 * third]),
        (2 * third, frames[2 * third:]),
    ]
    per_segment = max(1, (max_images - 2) // 3)
    picks = {0, len(frames) - 1}
    for offset, seg in segments:
        if not seg:
            continue
        step = max(1, int(round(len(seg) / float(per_segment))))
        for i in range(0, len(seg), step):
            picks.add(offset + i)
            if len(picks) >= max_images:
                break
        if len(picks) >= max_images:
            break

    if len(picks) < max_images:
        step = max(1, int(round(len(frames) / float(max_images))))
        for i in range(0, len(frames), step):
            picks.add(i)
            if len(picks) >= max_images:
                break

    return [frames[i] for i in sorted(picks)[:max_images]]


def _chunk_frames(frames: List[str], chunk_count: int) -> List[List[str]]:
    if chunk_count <= 1 or len(frames) <= 1:
        return [frames]

    chunk_count = min(chunk_count, len(frames))
    chunk_size = max(1, int(round(len(frames) / float(chunk_count))))
    chunks = []
    for i in range(0, len(frames), chunk_size):
        chunks.append(frames[i:i + chunk_size])
    return [chunk for chunk in chunks if chunk]


def vision_describe_event(
    frames: List[str],
    context: dict,
    max_images: int = 16,
    model: str = "llava:13b",
    debug: bool = False,
    segment_label: str | None = None,
) -> str:
    """
    Ask a vision model to describe what happens across frames.
    We cap images to keep latency stable.
    """
    chosen = _select_frames(frames, max_images)
    images_b64 = [_b64_image(p) for p in chosen]

    vision_prompt_path = os.path.join(BASE_DIR, "prompts", "vision.txt")
    fallback_prompt = (
        "You are a CCTV video analyst. Provide a concise factual timeline.\n"
        "Use three sections: EARLY / MIDDLE / LATE.\n"
        "Always compare EARLY vs LATE and note any object changes (added/removed/moved).\n"
        "Name concrete objects when visible (e.g., monitor, laptop, box, bag) but do not guess.\n"
        "Do NOT infer time-of-day or working-hours from the images.\n"
        "If unsure about an object, say 'unidentified object'.\n"
        "Be concise and accurate.\n"
    )
    prompt = _load_prompt(vision_prompt_path, fallback_prompt)
    intent = context.get("security_intent", {}) or {}
    if segment_label:
        prompt += f"\n\nSEGMENT: {segment_label}\n"
    prompt += (
        f"\n\nYou are given {len(chosen)} frames from the same clip. "
        "Do not ask for more images. Do not say frames are missing.\n"
        "\n\nCAMERA CONTEXT:\n"
        f"location: {context.get('camera_view', {}).get('location_name','Unknown')}\n"
        f"description: {context.get('camera_view', {}).get('description','')}\n"
        f"areas_of_interest: {json.dumps(context.get('areas_of_interest', []), ensure_ascii=False)}\n"
        f"what_is_normal: {json.dumps(intent.get('what_is_normal', []), ensure_ascii=False)}\n"
        f"what_is_suspicious: {json.dumps(intent.get('what_is_suspicious', []), ensure_ascii=False)}\n"
        f"primary_risks: {json.dumps(intent.get('primary_risks', []), ensure_ascii=False)}\n"
    )

    # Use vLLM only (no Ollama). If vLLM is disabled or fails, return empty string.
    if os.environ.get("USE_VLLM", "1") == "1":
        try:
            return vision_describe_event_vllm(
                frames=frames,
                context=context,
                max_images=max_images,
                model=model,
                vllm_host=VLLM_HOST,
                debug=debug,
                segment_label=segment_label,
            )
        except Exception as e:
            if debug:
                print(f"[AI-vLLM] vision_failed: {e}")
            return ""

    # If vLLM is not enabled, no other backend is supported.
    if debug:
        print("[AI] vision_no_backend: USE_VLLM is not enabled")
    return ""


def analyze_clip_temporal(
    frames: List[str],
    context: dict,
    model: str = "nemotron3:33b",
    debug: bool = False,
    window_count: int = 4,
    max_images_per_window: int = 8,
) -> str:
    """
    Build a clip-level narrative by analyzing multiple temporal windows.
    This keeps the pipeline frame-based while giving the model the whole motion story.
    """
    windows = _chunk_frames(frames, window_count)
    if not windows:
        return ""

    reports: List[str] = []
    total = len(windows)
    for index, window in enumerate(windows, start=1):
        label = f"window {index}/{total}"
        report = vision_describe_event(
            frames=window,
            context=context,
            max_images=min(max_images_per_window, len(window)),
            model=model,
            debug=debug,
            segment_label=label,
        )
        reports.append(f"{label.upper()}:\n{report}")

    return "\n\n".join(reports)


def analyze_clip_temporal_parallel(
    frames: List[str],
    context: dict,
    model: str = "nemotron3:33b",
    debug: bool = False,
    window_count: int = 4,
    max_images_per_window: int = 8,
    max_workers: int = 4,
) -> str:
    """
    Analyze temporal windows in PARALLEL using ThreadPoolExecutor.
    This can provide ~3-4x speedup by analyzing windows concurrently.
    
    Use when:
    - Multiple Ollama workers available or GPU supports concurrent inference
    - Faster response time is critical (real-time security monitoring)
    - System has sufficient memory (each window loads full model)
    
    Trade-off: Higher memory usage, potential rate limiting on Ollama server
    """
    windows = _chunk_frames(frames, window_count)
    if not windows:
        return ""

    def analyze_window(window_index: int, window: List[str]) -> tuple:
        """Analyze single window, return (index, report)."""
        label = f"window {window_index + 1}/{len(windows)}"
        try:
            report = vision_describe_event(
                frames=window,
                context=context,
                max_images=min(max_images_per_window, len(window)),
                model=model,
                debug=debug,
                segment_label=label,
            )
            return (window_index, f"{label.upper()}:\n{report}")
        except Exception as e:
            if debug:
                print(f"[AI] window {window_index} analysis failed: {e}")
            return (window_index, f"{label.upper()}:\n[Analysis failed]")

    # Submit all windows for concurrent analysis
    reports_dict = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(windows))) as executor:
        futures = {
            executor.submit(analyze_window, i, window): i
            for i, window in enumerate(windows)
        }
        
        for future in as_completed(futures):
            window_idx, report = future.result()
            reports_dict[window_idx] = report

    # Rebuild reports in original order
    reports = [reports_dict[i] for i in range(len(windows))]
    return "\n\n".join(reports)


def vision_describe_event_vllm(
    frames: List[str],
    context: dict,
    max_images: int = 16,
    model: str = "Chunity/gemma-4-E4B-it-AWQ-4bit",
    vllm_host: str = "http://vllm:8000",
    debug: bool = False,
    segment_label: str | None = None,
) -> str:
    """
    Use vLLM (OpenAI-compatible API) for frame analysis.
    vLLM is typically 2-5x faster than Ollama for large models.
    
    Args:
        frames: List of frame file paths
        context: Camera context dictionary
        max_images: Max frames to include
        model: Model name (used for logging only, vLLM loads from container)
        vllm_host: vLLM service host (e.g., http://vllm:8000)
        debug: Enable debug logging
        segment_label: Window label (e.g., "WINDOW 1/4")
    
    Returns:
        Analysis text or empty string on failure
    """
    chosen = _select_frames(frames, max_images)
    images_b64 = [_b64_image(p) for p in chosen]
    if not images_b64:
        return ""

    vision_prompt_path = os.path.join(BASE_DIR, "prompts", "vision.txt")
    fallback_prompt = (
        "You are a CCTV video analyst. Provide a concise factual timeline.\n"
        "Use three sections: EARLY / MIDDLE / LATE.\n"
        "Always compare EARLY vs LATE and note any object changes.\n"
        "Be concise and accurate.\n"
    )
    prompt = _load_prompt(vision_prompt_path, fallback_prompt)
    intent = context.get("security_intent", {}) or {}
    
    if segment_label:
        prompt += f"\n\nSEGMENT: {segment_label}\n"
    
    prompt += (
        f"\n\nYou are given {len(chosen)} frames from the same clip. "
        f"\n\nCAMERA CONTEXT:\n"
        f"location: {context.get('camera_view', {}).get('location_name','Unknown')}\n"
        f"description: {context.get('camera_view', {}).get('description','')}\n"
        f"areas_of_interest: {json.dumps(context.get('areas_of_interest', []), ensure_ascii=False)}\n"
        f"what_is_normal: {json.dumps(intent.get('what_is_normal', []), ensure_ascii=False)}\n"
        f"what_is_suspicious: {json.dumps(intent.get('what_is_suspicious', []), ensure_ascii=False)}\n"
        f"primary_risks: {json.dumps(intent.get('primary_risks', []), ensure_ascii=False)}\n"
    )

    # vLLM uses OpenAI-compatible /v1/chat/completions endpoint
    vllm_url = vllm_host.rstrip("/") + "/v1/chat/completions"
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    *[{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}} 
                      for b64 in images_b64]
                ]
            }
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        r = requests.post(vllm_url, json=payload, timeout=300)
        if not r.ok:
            print(f"[AI-vLLM] vision_failed status={r.status_code} body={r.text[:500]}")
            return ""
        data = r.json()
        response = _message_text(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
        
        if debug:
            print(f"[AI-vLLM] vision model={model} images={len(images_b64)} response_len={len(response)}")
        
        return response
    except Exception as e:
        print(f"[AI-vLLM] vision_failed err={e}")
        return ""


def analyze_clip_temporal_vllm(
    frames: List[str],
    context: dict,
    model: str = "Chunity/gemma-4-E4B-it-AWQ-4bit",
    vllm_host: str = "http://vllm:8000",
    debug: bool = False,
    window_count: int = 4,
    max_images_per_window: int = 8,
) -> str:
    """
    Analyze temporal windows using vLLM (much faster than Ollama).
    Sequential processing for simplicity; vLLM handles concurrency internally.
    """
    windows = _chunk_frames(frames, window_count)
    if not windows:
        return ""

    reports: List[str] = []
    total = len(windows)
    for index, window in enumerate(windows, start=1):
        label = f"window {index}/{total}"
        report = vision_describe_event_vllm(
            frames=window,
            context=context,
            max_images=min(max_images_per_window, len(window)),
            model=model,
            vllm_host=vllm_host,
            debug=debug,
            segment_label=label,
        )
        reports.append(f"{label.upper()}:\n{report}")

    return "\n\n".join(reports)


def analyze_clip_video(
    clip_path: str,
    context: dict,
    profile: dict,
    timeline: dict,
    model: str = "nemotron3:33b",
    debug: bool = False,
) -> str:
    """
    Send video clip directly to nemotron3:33b for whole-video temporal analysis.
    This exploits the model's native video understanding capability.
    Returns narrative text or empty string on failure (triggers fallback chain).
    """
    if not clip_path or not os.path.exists(clip_path):
        return ""

    try:
        # Encode video file as base64
        with open(clip_path, "rb") as f:
            video_data = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        if debug:
            print(f"[AI] video_encode_failed: {e}")
        return ""

    # Load video-specific prompt
    video_prompt_path = os.path.join(BASE_DIR, "prompts", "video_vision.txt")
    fallback_prompt = (
        "You are a professional CCTV security analyst. Analyze the entire video to provide "
        "a temporal narrative of events. Describe START (initial state), PROGRESSION (key transitions), "
        "and END (final state). Report behavioral indicators, suspicious movements, and signs of tampering. "
        "Be factual and report only what is visible."
    )
    prompt = _load_prompt(video_prompt_path, fallback_prompt)

    # Inject camera context into the prompt
    intent = context.get("security_intent", {}) or {}
    prompt += (
        f"\n\nCAMERA CONTEXT:\n"
        f"location: {context.get('camera_view', {}).get('location_name','Unknown')}\n"
        f"description: {context.get('camera_view', {}).get('description','')}\n"
        f"areas_of_interest: {json.dumps(context.get('areas_of_interest', []), ensure_ascii=False)}\n"
        f"what_is_normal: {json.dumps(intent.get('what_is_normal', []), ensure_ascii=False)}\n"
        f"what_is_suspicious: {json.dumps(intent.get('what_is_suspicious', []), ensure_ascii=False)}\n"
        f"primary_risks: {json.dumps(intent.get('primary_risks', []), ensure_ascii=False)}\n"
    )

    # Optional: include timeline context for temporal grounding
    if timeline:
        prompt += (
            f"\nEVENT TIMELINE:\n"
            f"label: {timeline.get('label', 'unknown')}\n"
            f"duration_sec: {timeline.get('duration_sec', 'unknown')}\n"
            f"top_score: {timeline.get('top_score', 'unknown')}\n"
        )

    # Use vLLM only for video analysis
    if os.environ.get("USE_VLLM", "1") == "1":
        try:
            return analyze_clip_video_vllm(
                clip_path=clip_path,
                context=context,
                vllm_host=VLLM_HOST,
                model=model,
                debug=debug,
                timeline=timeline,
            )
        except Exception as e:
            if debug:
                print(f"[AI-vLLM] video_api_failed: {e}")
            return ""

    if debug:
        print("[AI] video_no_backend: USE_VLLM is not enabled")
    return ""


def analyze_clip_video_vllm(
    clip_path: str,
    context: dict,
    vllm_host: str = "http://vllm:8000",
    model: str = "Chunity/gemma-4-E4B-it-AWQ-4bit",
    debug: bool = False,
    timeline: dict | None = None,
    max_tokens: int = 2048,
) -> str:
    """
    Send the entire video clip to vLLM using the OpenAI-compatible chat endpoint.
    Returns analysis text or empty string on failure.
    """
    if not clip_path or not os.path.exists(clip_path):
        return ""

    try:
        with open(clip_path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        if debug:
            print(f"[AI-vLLM] video_encode_failed: {e}")
        return ""

    video_prompt_path = os.path.join(BASE_DIR, "prompts", "video_vision.txt")
    fallback_prompt = (
        "You are a professional CCTV security analyst. Analyze the entire video to provide "
        "a temporal narrative of events. Describe START, PROGRESSION, and END. Be factual and "
        "report only what is visible."
    )
    prompt = _load_prompt(video_prompt_path, fallback_prompt)
    intent = context.get("security_intent", {}) or {}
    prompt += (
        f"\n\nCAMERA CONTEXT:\n"
        f"location: {context.get('camera_view', {}).get('location_name','Unknown')}\n"
        f"description: {context.get('camera_view', {}).get('description','')}\n"
        f"areas_of_interest: {json.dumps(context.get('areas_of_interest', []), ensure_ascii=False)}\n"
        f"what_is_normal: {json.dumps(intent.get('what_is_normal', []), ensure_ascii=False)}\n"
        f"what_is_suspicious: {json.dumps(intent.get('what_is_suspicious', []), ensure_ascii=False)}\n"
        f"primary_risks: {json.dumps(intent.get('primary_risks', []), ensure_ascii=False)}\n"
    )
    if timeline:
        prompt += (
            f"\nEVENT TIMELINE:\n"
            f"label: {timeline.get('label', 'unknown')}\n"
            f"duration_sec: {timeline.get('duration_sec', 'unknown')}\n"
            f"top_score: {timeline.get('top_score', 'unknown')}\n"
        )

    vllm_url = vllm_host.rstrip("/") + "/v1/chat/completions"

    # vLLM expects OpenAI-compatible messages. Attach the video as a data URL.
    video_data_url = f"data:video/mp4;base64,{video_b64}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "video_url", "video_url": {"url": video_data_url}},
                ],
            }
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }

    try:
        r = requests.post(vllm_url, json=payload, timeout=600)
        if not r.ok:
            print(f"[AI-vLLM] video_failed status={r.status_code} body={r.text[:500]}")
            return ""
        data = r.json()
        response_text = _message_text(data.get("choices", [{}])[0].get("message", {}).get("content", ""))

        if debug:
            print(f"[AI-vLLM] video model={model} response_len={len(response_text)}")

        return response_text
    except Exception as e:
        print(f"[AI-vLLM] video_api_failed: {e}")
        return ""


def _extract_json(txt: str) -> dict:
    start = txt.find("{")
    end = txt.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model did not return JSON.")
    return json.loads(txt[start:end + 1])


def _validate_decision(obj: dict) -> Optional[str]:
    missing = REQUIRED_DECISION_KEYS - set(obj.keys())
    if missing:
        return f"Missing keys: {sorted(missing)}"
    return None


def _write_raw_error(event_dir: str, txt: str) -> None:
    if not event_dir:
        return
    os.makedirs(event_dir, exist_ok=True)
    path = os.path.join(event_dir, "decision_raw.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(txt)


def decide_event_json(
    vision_text: str,
    timeline: dict,
    context: dict,
    profile: dict,
    in_working_hours: bool,
    event_dir: str,
    model: str = "qwen3:30b-a3b",
    debug: bool = False,
) -> Dict:
    """
    Ask a strong text model to output strict JSON decision.
    """
    decision_prompt_path = os.path.join(BASE_DIR, "prompts", "decision.txt")
    fallback_prompt = (
        "You are a security event analyst.\n"
        "Decide if this is a SECURITY EVENT worth storing. Output VALID JSON ONLY.\n"
        "Severity: 1 (low) to 5 (critical).\n"
        "Do not include any extra text outside JSON.\n\n"
        "Return JSON schema:\n"
        "{\n"
        '  "is_event": boolean,\n'
        '  "summary": string,\n'
        '  "category": string,\n'
        '  "severity": integer,\n'
        '  "reason": string,\n'
        '  "confidence": number\n'
        "}\n"
    )
    prompt = _load_prompt(decision_prompt_path, fallback_prompt)
    prompt += (
        "\n\nCAMERA CONTEXT:\n"
        f"{json.dumps(context, ensure_ascii=False)}\n\n"
        "PROFILE:\n"
        f"{json.dumps(profile, ensure_ascii=False)}\n\n"
        "EVENT TIMELINE:\n"
        f"{json.dumps(timeline, ensure_ascii=False)}\n\n"
        f"IN_WORKING_HOURS: {in_working_hours}\n\n"
        "VISION OBSERVATIONS:\n"
        f"{vision_text}\n"
    )

    # Prefer vLLM (OpenAI-compatible) when configured
    txt = ""
    resp_json = {}
    if os.environ.get("USE_VLLM", "1") == "1":
        try:
            vllm_url = VLLM_HOST.rstrip("/") + "/v1/chat/completions"
            # Strong system instruction to force JSON-only output matching the schema
            system_msg = (
                "You are a strict JSON generator. Given the user's CAMERA CONTEXT, PROFILE, TIMELINE, "
                "and VISION OBSERVATIONS, output VALID JSON and NOTHING ELSE. Do not add prose, quotes, "
                "or commentary. The JSON must match this schema exactly:\n"
                "{\n  \"is_event\": boolean,\n  \"summary\": string,\n  \"category\": string,\n  \"severity\": integer,\n  \"reason\": string,\n  \"confidence\": number\n}\n"
            )
            vpayload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": [{"type": "text", "text": system_msg}]},
                    {"role": "user", "content": [{"type": "text", "text": prompt}]},
                ],
                "temperature": 0.0,
                "max_tokens": 512,
            }
            r = requests.post(vllm_url, json=vpayload, timeout=300)
            if not r.ok:
                print(f"[AI-vLLM] decision_failed status={r.status_code} body={r.text[:500]}")
                txt = ""
                resp_json = {}
            else:
                resp = r.json()
                response = resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                txt = _message_text(response)
                resp_json = resp
                if debug:
                    print(f"[AI-vLLM] decision prompt_chars={len(prompt)} response_keys={list(resp.keys())}")
        except Exception as e:
            print(f"[AI-vLLM] decision_failed err={e}")
            txt = ""

    # If vLLM disabled or returned empty, do not call Ollama — return empty to trigger fallback decision logic upstream
    if not txt and debug:
        print("[AI] decision_no_vllm_response: falling back to local decision fallback")

    # If the model returned no textual response, save the full JSON for debugging.
    if not txt:
        try:
            if event_dir:
                os.makedirs(event_dir, exist_ok=True)
                dump_path = os.path.join(event_dir, "decision_raw.json")
                with open(dump_path, "w", encoding="utf-8") as f:
                    json.dump(resp_json, f, ensure_ascii=False, indent=2)
        except Exception:
            # best-effort only
            pass

    try:
        obj = _extract_json(txt)
    except Exception:
        _write_raw_error(event_dir, txt)
        raise ValueError(f"Model did not return valid JSON: {txt[:400]}")

    missing = _validate_decision(obj)
    if missing:
        _write_raw_error(event_dir, txt)
        raise ValueError(f"Invalid decision JSON: {missing}")
    return obj
