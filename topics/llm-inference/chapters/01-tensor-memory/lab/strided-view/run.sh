#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
mkdir -p out
gcc -std=c11 -O2 -Wall -Wextra -Werror -o out/view view.c
python3 check.py
