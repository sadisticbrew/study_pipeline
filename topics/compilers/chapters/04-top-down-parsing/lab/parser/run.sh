#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C GOTOOLCHAIN=local GOCACHE=/tmp/top-down-go-cache
printf '== Go ==\n'
go version
go run main.go parser.go driver.go
printf '\n'
go run compare.go
