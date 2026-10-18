# Left-recursion lab

Run from the repository root:

`python3 tools/lab.py run topics/compilers/chapters/04-top-down-parsing --only left-recursion`

## Source excerpts

- `main.go:15-30` (16 lines): naive self-call before token consumption, then Expr and
  Term loops that fold to the left. This is the recommended chapter include.
- `main.go:36-46` (11 lines): numeric and parenthesized factors.
- `main.go:47-55` (9 lines): tree rendering and evaluation.
- `capture.py:1-12` (12 lines): capture the child process's real diagnostics and exit
  status, without printing addresses or stack traces.

## Output sections

| `run.out` | Observation |
| --- | --- |
| `1-2` | Go version. |
| `3-6` | The naive parser's actual runtime stack-overflow diagnostic and exit status 2. |
| `7-9` | The loop parser's fully parenthesized tree and value 0. |

The child uses the default goroutine stack limit: no `debug.SetMaxStack` call is made.
The exact observed line is `runtime: goroutine stack exceeds 1000000000-byte limit`.
The fatal child process is anticipated; missing diagnostics or an unexpected success make
the enclosing lab fail. The whole lab expects success.

Two-line output summary:
The naive parser reports the default 1,000,000,000-byte stack limit and exits with status 2.
The loop parser prints `((10 - 4) - (3 * 2))` and `value: 0`.

No DOT figures are generated. `out/parser` is the compiled executable.
