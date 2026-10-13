#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C GOTOOLCHAIN=local GOCACHE=/tmp/exprc-go-cache
ulimit -c 0
# Keep the compiler binary outside the directory whose artifacts we observe.
go build -o /tmp/exprc main.go
python3 observe.py /tmp/exprc
