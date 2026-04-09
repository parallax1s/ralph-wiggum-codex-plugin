#!/usr/bin/env bash
set -euo pipefail

LOG_PATH="${FAKE_DETACHED_TARGET_LOG:-}"
SLEEP_SECONDS="${FAKE_DETACHED_TARGET_SLEEP_SECONDS:-3}"

if [[ -n "${LOG_PATH}" ]]; then
  mkdir -p "$(dirname "${LOG_PATH}")"
  printf 'started\n' >> "${LOG_PATH}"
fi

sleep "${SLEEP_SECONDS}"
