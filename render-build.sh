#!/usr/bin/env bash
# Install Python dependencies
poetry install --no-root

# Install Playwright browsers (no sudo required)
poetry run playwright install chromium

# Optional: Ensure headless mode works cleanly
export PLAYWRIGHT_BROWSERS_PATH=/opt/render/.cache/ms-playwright
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0
