#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

bash scripts/install-git-hooks.sh

# Conventional-only: validate Conventional Commits v1.0.0 header/footer syntax.
git config --local jh.hooks.commitmsg.gate false
git config --local jh.hooks.commitmsg.conventional true

echo "OK: enabled Conventional Commits check only"
echo " - jh.hooks.commitmsg.gate=false"
echo " - jh.hooks.commitmsg.conventional=true"

