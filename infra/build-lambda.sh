#!/usr/bin/env bash
# Build the Lambda deployment asset WITHOUT Docker.
# Installs deps as Linux (manylinux) wheels for the Lambda runtime and copies
# the career_copilot package alongside them into infra/build/.
# Run before `cdk deploy`.
set -euo pipefail
cd "$(dirname "$0")"

BUILD=build
rm -rf "$BUILD" && mkdir -p "$BUILD"

echo "Installing deps as manylinux (Python 3.13) wheels..."
python3 -m pip install \
  --platform manylinux2014_x86_64 \
  --implementation cp \
  --python-version 3.13 \
  --only-binary=:all: \
  --upgrade \
  --target "$BUILD" \
  -r ../src/requirements.txt

echo "Copying career_copilot package..."
cp -r ../src/career_copilot "$BUILD/career_copilot"

# Trim test/cache cruft to keep the zip small.
find "$BUILD" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find "$BUILD" -type d -name "*.dist-info" -prune -exec rm -rf {} + 2>/dev/null || true

echo "Built asset in infra/$BUILD ($(du -sh "$BUILD" | cut -f1))"
