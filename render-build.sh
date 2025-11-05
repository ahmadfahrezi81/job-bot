#!/usr/bin/env bash
# Render build script for job-bot

set -o errexit  # Exit on error

echo "🚀 Installing dependencies with Poetry..."
poetry install --no-root

echo "🎭 Installing Playwright browsers (for crawl fallback)..."
poetry run playwright install chromium

echo "✅ Build completed successfully!"
