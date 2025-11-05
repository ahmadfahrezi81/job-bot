#!/usr/bin/env bash
# Render build script

set -o errexit  # Exit on error

# Install dependencies using Poetry
echo "🚀 Installing dependencies with Poetry..."
poetry install --no-root

# (Optional) If you need to build Playwright dependencies, add this:
echo "🎭 Installing Playwright browsers..."
poetry run playwright install chromium
