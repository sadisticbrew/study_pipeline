#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
export LAB_CFLAGS='-std=c11 -O2 -Wall -Wextra -Werror -fno-lto -fno-loop-interchange -fno-tree-loop-vectorize -fno-tree-slp-vectorize -fno-unroll-loops'
mkdir -p out
gcc $LAB_CFLAGS -S kernels.c -o out/kernels.s
gcc $LAB_CFLAGS -c kernels.c -o out/kernels.o
gcc $LAB_CFLAGS bench.c out/kernels.o -o out/bench
python3 measure.py
