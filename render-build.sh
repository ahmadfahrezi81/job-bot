#!/usr/bin/env bash
# Render build script for Job Bot

set -o errexit  # Exit on error

echo "🚀 Installing dependencies with Poetry..."
poetry install --no-root

echo "🎭 Installing Playwright browsers..."
# This ensures Chromium and dependencies are downloaded
poetry run playwright install --with-deps chromium

echo "✅ Build completed successfully."
