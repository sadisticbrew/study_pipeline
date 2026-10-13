#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C GOTOOLCHAIN=local GOCACHE=/tmp/lexing-go-cache
printf '== Go ==\n'
go version
go run main.go driver.go
