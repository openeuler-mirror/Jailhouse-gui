#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

bash scripts/install-git-hooks.sh

# Gate-only: enforce local policy trailers (Signed-off-by/Tags, etc.)
git config --local jh.hooks.commitmsg.gate true
git config --local jh.hooks.commitmsg.conventional false

echo "OK: enabled commit message gate only"
echo " - jh.hooks.commitmsg.gate=true"
echo " - jh.hooks.commitmsg.conventional=false"
