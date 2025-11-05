#!/usr/bin/env bash
set -o errexit

echo "🚀 Installing dependencies with Poetry..."
poetry install --no-interaction --no-root
