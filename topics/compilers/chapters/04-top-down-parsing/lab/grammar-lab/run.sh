#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
printf '== Python ==\n'
python3 --version
python3 grammar.py
