#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C GOTOOLCHAIN=local GOCACHE=/tmp/left-recursion-go-cache
ulimit -c 0
printf '== Go ==\n'
go version
mkdir -p out
go build -o out/parser main.go
python3 capture.py
printf '== Loop parser ==\n'
./out/parser
