#!/usr/bin/env bash
set -euo pipefail

BASE_REF="${GITHUB_BASE_REF:-${BASE_REF:-main}}"
WORKING_DIRECTORY="${WORKING_DIRECTORY:-.}"
OUTPUT_DIR="${OUTPUT_DIR:-.ai}"

mkdir -p "${OUTPUT_DIR}"

git fetch origin "${BASE_REF}" --depth=1 >/dev/null 2>&1 || true

BASE_SHA="$(git merge-base HEAD "origin/${BASE_REF}")"

git diff --name-only "${BASE_SHA}"...HEAD -- "${WORKING_DIRECTORY}" > "${OUTPUT_DIR}/changed-files.txt"

git diff \
  --unified=0 \
  --no-ext-diff \
  "${BASE_SHA}"...HEAD \
  -- \
  "${WORKING_DIRECTORY}" \
  ':!**/target/**' \
  ':!**/build/**' \
  ':!**/.mvn/**' \
  ':!**/*.lock' \
  ':!**/package-lock.json' \
  ':!**/yarn.lock' \
  ':!**/*.png' \
  ':!**/*.jpg' \
  ':!**/*.jpeg' \
  ':!**/*.gif' \
  ':!**/*.pdf' \
  > "${OUTPUT_DIR}/diff.patch"