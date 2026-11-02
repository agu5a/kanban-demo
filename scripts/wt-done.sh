#!/usr/bin/env bash
# Finish issue <n>: rebase on origin/main, mise run check, push, open the PR, wait for CI,
# remove the worktree, squash merge. The board moves to Done via the project's built-in workflows.
set -euo pipefail

usage="usage: wt-done.sh <issue>"
n=${1:?$usage}
case $n in '' | *[!0-9]*) echo "$usage" >&2 && exit 2 ;; esac

main=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")
cd "$main"

wt=$(git worktree list --porcelain | awk -v b="refs/heads/$n-" '
  /^worktree / { w = substr($0, 10) }
  /^branch / && index($2, b) == 1 { print w }')
if [ -z "$wt" ] || [ "$(wc -l <<<"$wt")" -ne 1 ]; then
  echo "Expected exactly one worktree on a '$n-*' branch, found: ${wt:-none}" >&2
  exit 1
fi
branch=$(git -C "$wt" branch --show-current)

if [ -n "$(git -C "$wt" status --porcelain)" ]; then
  echo "Uncommitted changes in $wt" >&2
  exit 1
fi

unset VIRTUAL_ENV

git -C "$wt" fetch -q origin
if ! git -C "$wt" rebase -q origin/main; then
  echo "Rebase conflict in $wt: resolve it, run 'git rebase --continue', then rerun wt-done.sh $n" >&2
  exit 1
fi
# Tests after the rebase catch semantic conflicts that merge cleanly as text
(cd "$wt" && mise run check)
git -C "$wt" push -q --force-with-lease -u origin "$branch"

if ! gh pr view "$branch" >/dev/null 2>&1; then
  (cd "$wt" && gh pr create --head "$branch" --fill --body "Closes #$n")
fi

# Checks show up a few seconds after the push
for _ in $(seq 1 30); do
  [ "$(gh pr view "$branch" --json statusCheckRollup --jq '.statusCheckRollup | length')" -gt 0 ] && break
  sleep 2
done
gh pr checks "$branch" --watch --fail-fast

git worktree remove "$wt"
gh pr merge "$branch" --squash --delete-branch
git pull -q --ff-only
echo "#$n merged"
