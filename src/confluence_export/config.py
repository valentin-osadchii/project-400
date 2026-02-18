"""Configuration loading from YAML files and CLI args."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Config:
    base_url: str = ""
    page_id: str = ""
    out: str = ""
    token_env: str = "CONFLUENCE_TOKEN"
    api_mode: str = "v2"
    ca_cert: str = ""

    def token(self) -> str:
        val = os.environ.get(self.token_env, "")
        if not val:
            raise SystemExit(
                f"Error: environment variable '{self.token_env}' is not set or empty."
            )
        return val


def load_config(path: str | Path) -> Config:
    """Load a YAML config file and return a Config with those values."""
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    known_keys = {f.name for f in Config.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in known_keys and v is not None}
    return Config(**filtered)


def merge_cli_into_config(cfg: Config, cli_args: dict) -> Config:
    """Override config values with any non-None CLI arguments."""
    for key, val in cli_args.items():
        if val is not None and hasattr(cfg, key):
            setattr(cfg, key, val)
    return cfg
