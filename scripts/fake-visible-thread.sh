#!/usr/bin/env bash
set -euo pipefail

LOG_PATH="${FAKE_VISIBLE_THREAD_LOG:-}"
THREAD_ID=""
MESSAGE=""
TIMEOUT_MS=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --thread-id)
      THREAD_ID="${2:-}"
      shift 2
      ;;
    --message)
      MESSAGE="${2:-}"
      shift 2
      ;;
    --timeout-ms)
      TIMEOUT_MS="${2:-}"
      shift 2
      ;;
    *)
      echo "Unknown arg: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -n "${LOG_PATH}" ]]; then
  mkdir -p "$(dirname "${LOG_PATH}")"
  {
    printf 'THREAD_ID=%s\n' "${THREAD_ID}"
    printf 'TIMEOUT_MS=%s\n' "${TIMEOUT_MS}"
    printf 'MESSAGE=%s\n' "${MESSAGE}"
  } >> "${LOG_PATH}"
fi

printf 'visible iteration ok\n<promise>%s</promise>\n' "${FAKE_VISIBLE_THREAD_COMPLETE_PROMISE:-COMPLETE}"
