# Setup and integration

Prerequisites: Docker Compose; an authorized RTSP/test source; a compatible Frigate release; a separately hosted video-capable vLLM endpoint and a local text endpoint. Ollama is available through environment configuration and optional frame/decision paths. No GPU server or model is started by this Compose example.

1. Copy `.env.example` to ignored `.env`. Set `VLLM_VIDEO_MODEL` and `VLLM_TEXT_MODEL` to the exact names served by your local endpoint. Set URLs reachable from the worker container.
2. Review `config/config.yaml`. The demo camera is disabled. Configure an authorized stream without committing its URL or credentials. Align the camera ID with its worker context YAML.
3. Run `docker compose config --quiet` to validate interpolation, then `docker compose up --build -d`. Keep Frigate and the broker on the isolated Compose network.
4. Use the local console for camera/profile context. Prompts live under `frigate-ollama-realtime/prompts/`; business-hour and alert thresholds live in camera contexts and profiles.
5. Candidate clips and per-event artifacts are stored under `local-data/worker-work`; JSONL/decision output is stored under `local-data/worker-out`. These are ignored and must remain private.

The broker permits anonymous clients only within the isolated lab network. The console proxies Frigate's internal API and the worker's unauthenticated admin API. All externally published ports bind to loopback. A production deployment needs authentication, a protected broker, TLS, retention policy, and a dedicated model/runtime compatibility review.

Validation for publication covered Python syntax, YAML parsing, Compose interpolation, privacy/secret checks, and sample data. It did not connect to a company camera or execute GPU inference.
