#!/usr/bin/env bash
set -euo pipefail

unexpected="$(
  find src -mindepth 1 -maxdepth 1 \( -type d -o -name '*.py' \) \
    ! -name 'builddrone' \
    ! -name '*.egg-info' \
    -print | sort
)"
if [ -n "${unexpected}" ]; then
  echo "Unexpected top-level packages or modules under src/; refusing to continue:" >&2
  echo "${unexpected}" >&2
  exit 1
fi

for candidate in sitecustomize.py usercustomize.py sitecustomize usercustomize; do
  if [ -e "${candidate}" ]; then
    echo "Forbidden auto-imported module present: ${candidate}" >&2
    exit 1
  fi
done
