"""Fetch Confluence page content via REST API."""

from __future__ import annotations

import time

import requests

from confluence_export.config import Config


_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0  # seconds


def fetch_page_storage(cfg: Config) -> str:
    """Fetch the storage-format body of a Confluence page.

    Returns the raw XHTML/storage-format string.
    """
    token = cfg.token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    if cfg.api_mode == "v2":
        url = f"{cfg.base_url.rstrip('/')}/api/v2/pages/{cfg.page_id}?body-format=storage"
    else:
        url = f"{cfg.base_url.rstrip('/')}/rest/api/content/{cfg.page_id}?expand=body.storage"

    verify = cfg.ca_cert if cfg.ca_cert else True
    resp = _request_with_retry(url, headers, verify=verify)

    data = resp.json()
    if cfg.api_mode == "v2":
        return data["body"]["storage"]["value"]
    else:
        return data["body"]["storage"]["value"]


def _request_with_retry(url: str, headers: dict, *, verify=True) -> requests.Response:
    """GET with exponential backoff on 429 and 5xx."""
    for attempt in range(_MAX_RETRIES + 1):
        resp = requests.get(url, headers=headers, timeout=30, verify=verify)

        if resp.status_code == 401:
            raise SystemExit("Error: 401 Unauthorized — check your API token.")
        if resp.status_code == 403:
            raise SystemExit("Error: 403 Forbidden — insufficient permissions for this page.")
        if resp.status_code == 404:
            raise SystemExit(f"Error: 404 Not Found — page not found at {url}")

        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt < _MAX_RETRIES:
                wait = _BACKOFF_BASE * (2 ** attempt)
                time.sleep(wait)
                continue
            resp.raise_for_status()

        resp.raise_for_status()
        return resp

    raise RuntimeError("Unreachable")
