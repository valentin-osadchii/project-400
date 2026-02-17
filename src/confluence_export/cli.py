"""CLI entry point for confluence_export."""

from __future__ import annotations

import argparse
import sys

from confluence_export.config import Config, load_config, merge_cli_into_config
from confluence_export.main import run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="confluence_export",
        description="Download a Confluence Cloud page and convert to Sphinx/MyST Markdown.",
    )
    p.add_argument("--base-url", dest="base_url", help="Confluence Cloud base URL (include /wiki if needed)")
    p.add_argument("--page-id", dest="page_id", help="Page content ID")
    p.add_argument("--out", help="Output markdown file path")
    p.add_argument("--token-env", dest="token_env", default=None, help="Env var name for the API token (default: CONFLUENCE_TOKEN)")
    p.add_argument("--api-mode", dest="api_mode", choices=["v1", "v2"], default=None, help="API mode: v1 or v2 (default: v2)")
    p.add_argument("--config", dest="config_file", default=None, help="Optional YAML config file")
    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.config_file:
        cfg = load_config(args.config_file)
    else:
        cfg = Config()

    cli_vals = {
        "base_url": args.base_url,
        "page_id": args.page_id,
        "out": args.out,
        "token_env": args.token_env,
        "api_mode": args.api_mode,
    }
    cfg = merge_cli_into_config(cfg, cli_vals)

    if not cfg.base_url or not cfg.page_id or not cfg.out:
        parser.error("--base-url, --page-id, and --out are required (via CLI or config file).")

    run(cfg)
