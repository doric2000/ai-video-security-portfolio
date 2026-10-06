# Architecture and tradeoffs

![Pipeline](architecture.svg)

`mqtt_ingest.py` tracks Frigate event lifecycle. On a closed person event, `main.py` checks camera context and policy (confidence, hours, loitering), filters duplicates, downloads evidence through `frigate_client.py`, and builds temporal context in `evidence.py`.

The primary video path calls the configured vLLM service through `ollama_analyzer.py`. When explicitly enabled, a frame-based fallback creates an evidence pack and analyzes temporal windows. A separate decision step produces structured fields; `writers.py` records JSON, text, and JSONL artifacts. Threshold-qualified decisions can update Frigate through its API. This is an integration layer around upstream detection and inference systems.

Contextual gating reduces unnecessary inference calls, but a missed gate prevents downstream review. A bounded in-memory deduplication cache simplifies operation but does not guarantee exactly-once processing across restarts. Model confidence is not a statistical guarantee. Retention, access control, model licensing, and hardware compatibility require environment-specific decisions before production use.
