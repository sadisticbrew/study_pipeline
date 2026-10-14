# Left-recursion lab

Run from the repository root with `python3 tools/lab.py run topics/compilers/chapters/04-top-down-parsing --only left-recursion`.

The naive function follows `Expr -> Expr - Term | Term`, calling itself before inspecting lookahead. Only the naive child process lowers its goroutine-stack limit to 32768 bytes with `debug.SetMaxStack`; this is not the Go runtime's default limit. `run.sh` builds into a temporary directory, captures the child failure, prints the initial observations and runtime errors without unstable stack addresses, then runs the loop version. The lab expects overall success, not failure. `GOTRACEBACK=none` avoids a long trace. The fixed parser is deliberately just the subtraction/multiplication subset needed for the opening expression; the book's full parser is the sibling `parser` lab.

## Source excerpts

Paths are relative to this lab directory.

- `main.go:20-28`: naive left-recursive function.
- `main.go:30-38`: loop version folding into the left child.
- `main.go:55-68`: multiplication level and tree/value combination.
- `main.go:70-82`: input, process-local lowered stack limit and observation printing.
- `run.sh:9-23`: bounded runtime-error capture, child exit status and fixed run.

## Output excerpts

- `run.out:1-2`: Go version.
- `run.out:4-9`: input, zero initially consumed tokens, configured stack limit, runtime stack-overflow messages, and child exit status 2. Runtime addresses are omitted from captured output.
- `run.out:11-14`: loop version's tree `((10 - 4) - (3 * 2))`, value 0, seven consumed tokens and EOF lookahead.

The captured child reports a 32768-byte stack limit and a fatal stack overflow, then exits with status 2.
The fixed run prints the left-leaning subtraction tree, value 0, and EOF after seven tokens.
