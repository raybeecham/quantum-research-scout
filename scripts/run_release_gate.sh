#!/usr/bin/env bash
# Fail closed on errors AND hangs; keep the exact-artifact checks and their logs.
set -euo pipefail

run_check() {
  local name="$1" budget="$2"
  shift 2
  mkdir -p site/verification/gate
  echo "::group::Release gate: $name (limit $budget)"
  local status=0
  # GNU timeout terminates the process group, including browser descendants.
  # SIGKILL bounds cleanup even if a browser ignores SIGTERM.
  timeout --kill-after=15s "$budget" "$@" 2>&1 | tee "site/verification/gate/$name.log" || status=$?
  echo "::endgroup::"
  if (( status != 0 )); then
    echo "::error::Release gate $name failed (exit $status; budget $budget). Publication blocked."
    return "$status"
  fi
}

main() {
  mkdir -p site/verification/gate
  python -u -m http.server 8765 --bind 127.0.0.1 --directory site >site/verification/gate/server.log 2>&1 &
  preview_pid=$!
  trap 'kill "$preview_pid" 2>/dev/null || true' EXIT
  for check in frontier_round2 lazy_data round4 hourly_news tab_cleanup conferences; do
    run_check "$check" 5m python -u "scripts/verify_${check}_browser.py" --channel chromium
  done
  run_check accessibility 10m python -u scripts/verify_accessibility_browser.py --channel chromium
  run_check publication 10m xvfb-run -a python -u scripts/verify_publication_gate.py --channel chromium --headed
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
