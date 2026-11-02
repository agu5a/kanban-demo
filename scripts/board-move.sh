#!/usr/bin/env bash
# Move issue <n> to a Status column on the project board; adds the issue to the board if missing.
# IDs are looked up on every run, so nothing goes stale.
set -euo pipefail

OWNER=agu5a
PROJECT=2
REPO=agu5a/kanban-demo
usage="usage: board-move.sh <issue> <Todo|In Progress|Done>"

n=${1:?$usage}
status=${2:?$usage}
case $n in '' | *[!0-9]*) echo "$usage" >&2 && exit 2 ;; esac

project_id=$(gh project view "$PROJECT" --owner "$OWNER" --format json --jq .id)
field_json=$(gh project field-list "$PROJECT" --owner "$OWNER" --format json \
  --jq '.fields[] | select(.name == "Status")')
field_id=$(jq -r .id <<<"$field_json")
option_id=$(jq -r --arg s "$status" '.options[] | select(.name == $s) | .id' <<<"$field_json")
if [ -z "$option_id" ]; then
  echo "Unknown status: $status (options: $(jq -r '[.options[].name] | join(", ")' <<<"$field_json"))" >&2
  exit 2
fi

item_id=$(gh project item-list "$PROJECT" --owner "$OWNER" --format json --limit 500 \
  --jq ".items[] | select(.content.type == \"Issue\" and .content.repository == \"$REPO\" and .content.number == $n) | .id")
if [ -z "$item_id" ]; then
  url=$(gh issue view "$n" --repo "$REPO" --json url --jq .url)
  item_id=$(gh project item-add "$PROJECT" --owner "$OWNER" --url "$url" --format json --jq .id)
fi

gh project item-edit --id "$item_id" --project-id "$project_id" --field-id "$field_id" \
  --single-select-option-id "$option_id" >/dev/null
echo "#$n -> $status"
