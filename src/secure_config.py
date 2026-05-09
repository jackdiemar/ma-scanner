#!/usr/bin/env python3
"""Runtime-only configuration helpers for secrets and private settings."""

import os


def get_env(name, default=""):
    return os.getenv(name, default).strip()


def require_env(name):
    value = get_env(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_csv_env(name, default=""):
    value = get_env(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]
