#!/usr/bin/env bash
set -euo pipefail

MODE="${FAKE_CODEX_MODE:-complete}"
LOG_PATH="${FAKE_CODEX_LOG:-}"
PROMPT="${*: -1}"

if [[ -n "${LOG_PATH}" ]]; then
  mkdir -p "$(dirname "${LOG_PATH}")"
  printf '%s\n' "$*" >>"${LOG_PATH}"
fi

case "${MODE}" in
  complete)
    printf 'iteration ok\n<promise>%s</promise>\n' "${FAKE_CODEX_COMPLETE_PROMISE:-COMPLETE}"
    ;;
  abort)
    printf 'blocked\n<promise>%s</promise>\n' "${FAKE_CODEX_ABORT_PROMISE:-ABORT}"
    ;;
  echo)
    printf '%s\n' "${PROMPT}"
    ;;
  sleep)
    sleep "${FAKE_CODEX_SLEEP_SECONDS:-30}"
    printf 'woke up\n'
    ;;
  *)
    echo "Unknown FAKE_CODEX_MODE: ${MODE}" >&2
    exit 1
    ;;
esac
