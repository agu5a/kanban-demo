#!/bin/bash
# Rebuild the demo SQLite database with demo items
# Run from the repo root (where todo.py is)

set -euo pipefail

cd "$(dirname "$0")/.."

echo "Removing existing data/todos.db..."
rm -f data/todos.db

echo "Creating demo database..."
.venv/bin/python -c "
import todo
todo.init_demo_db('data/todos.db')
"

echo "Demo database rebuilt:"
.venv/bin/python todo.py list