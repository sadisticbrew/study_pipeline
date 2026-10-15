#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
ulimit -c 0
mkdir -p out
gcc -O0 -g -fcf-protection=none -o fact fact.c
systemslab record --strict --quiet -o out/fact.slt -- ./fact
systemslab stack out/fact.slt 'fact+0xc@3'
systemslab dot stack out/fact.slt 'fact+0xc@3' > out/stack-fact3.dot
systemslab check-abi out/fact.slt
