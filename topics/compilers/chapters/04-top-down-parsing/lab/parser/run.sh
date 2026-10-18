#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C GOTOOLCHAIN=local GOCACHE=/tmp/parser-go-cache
printf '== Go ==\n'
go version
go run lexer.go parser.go main.go
