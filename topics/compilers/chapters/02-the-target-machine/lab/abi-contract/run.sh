#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
ulimit -c 0
python3 observe.py
