#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C GOTOOLCHAIN=local GOCACHE=/tmp/lexing-real-go-cache
printf '== Tool versions ==\n'
go version
flex --version
gcc -dumpfullversion
printf '\n== go/scanner semicolon insertion ==\n'
go run scanner.go
printf '\n== flex: keyword before identifier ==\n'
flex -o /tmp/lexing-tokens.c tokens.l
gcc -o /tmp/lexing-tokens /tmp/lexing-tokens.c
printf '%s\n' 'if x1 <= 10 { y = x1 * 2 } // done' | /tmp/lexing-tokens
printf '\n== flex: identifier before keyword ==\n'
flex -o /tmp/lexing-swapped.c swapped.l
gcc -o /tmp/lexing-swapped /tmp/lexing-swapped.c
printf '%s\n' 'if x1 <= 10 { y = x1 * 2 } // done' | /tmp/lexing-swapped
printf '\n== gcc: x+++++y ==\n'
status=0
gcc -fsyntax-only -fdiagnostics-color=never munch.c || status=$?
printf 'exit=%d\n' "$status"
if [[ "$status" -eq 0 ]]; then exit 1; fi
printf '\n== gcc: x++ + ++y ==\n'
status=0
gcc -fsyntax-only -fdiagnostics-color=never spaced.c || status=$?
printf 'exit=%d\n' "$status"
exit "$status"
