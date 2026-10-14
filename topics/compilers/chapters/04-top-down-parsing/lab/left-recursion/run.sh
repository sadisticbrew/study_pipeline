#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C GOTOOLCHAIN=local GOCACHE=/tmp/top-down-go-cache GOTRACEBACK=none
printf '== Go ==\n'
go version
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
go build -o "$work/recursion" main.go
printf '\n== Naive left recursion ==\n'
set +e
"$work/recursion" naive >"$work/crash" 2>&1
status=$?
set -e
# Retain observations and runtime errors, omitting unstable stack addresses.
for ((line=0; line<5; line++)); do
    IFS= read -r text || break
    case "$text" in "runtime: sp="*) continue ;; esac
    printf '%s\n' "$text"
done <"$work/crash"
printf 'exit status = %d\n' "$status"
if [[ $status -eq 0 ]]; then exit 1; fi
printf '\n== Loop and left fold ==\n'
"$work/recursion"
