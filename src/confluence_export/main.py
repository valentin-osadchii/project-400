"""Orchestrator: fetch → convert → write."""

from __future__ import annotations

from pathlib import Path

from confluence_export.config import Config
from confluence_export.converter import convert_html
from confluence_export.fetch import fetch_page_storage


def run(cfg: Config) -> None:
    """Execute the full export pipeline."""
    print(f"Fetching page {cfg.page_id} from {cfg.base_url} (api_mode={cfg.api_mode})...")
    html = fetch_page_storage(cfg)

    print("Converting to Markdown...")
    md = convert_html(html)

    out_path = Path(cfg.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"Written to {out_path}")
