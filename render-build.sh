#!/usr/bin/env bash
set -eux

uv sync  # Install dependencies
uv run playwright install --with-deps chromium
