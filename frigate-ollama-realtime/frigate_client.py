# Frigate HTTP client for clips/snapshots.
# English comments only.

import os
from typing import Any, Optional

import requests


class FrigateClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def _request(self, method: str, path: str, json_body: Optional[dict[str, Any]] = None) -> requests.Response:
        url = f"{self.base_url}{path}"
        response = self.session.request(method, url, json=json_body, timeout=300)
        response.raise_for_status()
        return response

    def download_event_clip(self, event_id: str, out_path: str) -> str:
        """
        Downloads /api/events/<id>/clip.mp4
        """
        url = f"{self.base_url}/api/events/{event_id}/clip.mp4"
        r = requests.get(url, timeout=300)
        r.raise_for_status()

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(r.content)
        return out_path

    def set_event_description(self, event_id: str, description: str) -> None:
        self._request("POST", f"/api/events/{event_id}/description", {"description": description})

    def set_event_sub_label(self, event_id: str, sub_label: str, score: float | None = None) -> None:
        body: dict[str, Any] = {"subLabel": sub_label}
        if score is not None:
            body["subLabelScore"] = score
        self._request("POST", f"/api/events/{event_id}/sub_label", body)

    def retain_event(self, event_id: str) -> None:
        self._request("POST", f"/api/events/{event_id}/retain")
