#!/usr/bin/env bash
# Start work on issue <n>: branch via gh issue develop, worktree next to the main checkout,
# mise setup, board "In Progress". Prints the cd command for the new worktree.
set -euo pipefail

usage="usage: wt-new.sh <issue> [slug]"
n=${1:?$usage}
case $n in '' | *[!0-9]*) echo "$usage" >&2 && exit 2 ;; esac

scripts=$(cd "$(dirname "$0")" && pwd)
main=$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")
cd "$main"

if [ $# -ge 2 ]; then
  slug=$2
else
  slug=$(gh issue view "$n" --json title --jq .title |
    tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | cut -c1-30 | sed 's/^-*//; s/-*$//')
fi
branch="$n-$slug"
wt="$main.worktrees/$branch"

# An inherited venv (e.g. from a VS Code terminal) must not leak into mise tasks
unset VIRTUAL_ENV

git fetch -q origin
if ! git ls-remote --exit-code --heads origin "$branch" >/dev/null; then
  gh issue develop "$n" --name "$branch" --base main >/dev/null
  git fetch -q origin
fi
git worktree add -q "$wt" "$branch"
(cd "$wt" && mise trust -q && mise run setup >/dev/null)
"$scripts/board-move.sh" "$n" "In Progress"

echo "cd $wt"
