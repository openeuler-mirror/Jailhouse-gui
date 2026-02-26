#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
hooks_dir=".githooks"
hooks=(pre-commit commit-msg commit-msg.gate commit-msg.conventional)

if ! command -v git >/dev/null 2>&1; then
  echo "error: git not found in PATH" >&2
  exit 1
fi

cd "$repo_root"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: not inside a git worktree: ${repo_root}" >&2
  exit 1
fi

if [[ ! -d "${hooks_dir}" ]]; then
  echo "error: missing ${hooks_dir}/ (repo-local hooks directory not found)" >&2
  exit 1
fi

for h in "${hooks[@]}"; do
  if [[ ! -f "${hooks_dir}/${h}" ]]; then
    echo "error: missing hook: ${hooks_dir}/${h}" >&2
    exit 1
  fi
done

# Use a repo-local hooks directory so teammates get the same gate behavior.
# --local ensures we only touch this repository's config.
git config --local core.hooksPath "${hooks_dir}"

chmod +x "${hooks_dir}/pre-commit" "${hooks_dir}/commit-msg" "${hooks_dir}/commit-msg.gate" "${hooks_dir}/commit-msg.conventional"

echo "OK: installed git hooks via core.hooksPath=$(git config --local --get core.hooksPath)"
echo "Tip: to uninstall -> git config --local --unset core.hooksPath"
echo "Tip: select commit-msg checks -> git config --local jh.hooks.commitmsg.gate <true|false> ; git config --local jh.hooks.commitmsg.conventional <true|false>"
