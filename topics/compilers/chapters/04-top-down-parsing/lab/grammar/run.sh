#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
printf '== Python ==\n'
python3 --version
python3 main.py
if command -v dot >/dev/null 2>&1; then
    for name in tree-0 tree-6 layered rewritten; do
        dot -Tsvg "out/$name.dot" -o "out/$name.svg"
    done
fi
