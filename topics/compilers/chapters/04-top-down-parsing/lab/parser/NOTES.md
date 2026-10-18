# Parser lab

Run from the repository root:

`python3 tools/lab.py run topics/compilers/chapters/04-top-down-parsing --only parser`

`lexer.go` is an unchanged copy of chapter 3's `lab/lexer/main.go`. The parser accepts
programs with function declarations, all five statement alternatives, optional else
blocks or else-if, parameters, calls, parentheses and prefix minus. It stops at the first
syntax error; there is no recovery. `parseExpr(1)` is the expression entry point.

## Source excerpts

- `parser.go:44-65` (22 lines): `parseStmt` chooses the production by lookahead.
- `parser.go:67-86` (20 lines): binding powers and Pratt loop; right operands use `power + 1`.
- `parser.go:96-117` (22 lines): primary expressions and prefix minus with minimum 6.
- `parser.go:88-95` (8 lines): tracing hook; rendering happens only with tracing enabled.
- `main.go:9-17` (9 lines): standard-library AST converted to the same tree notation.

Prefer only the first two source excerpts in the chapter. Together with grammar's
`69-77` and `94-103`, left-recursion's `15-30`, and eval-order's `5-12`, the suggested
chapter includes total 85 lines of code.

## Output sections

| `run.out` | Observation |
| --- | --- |
| `1-2` | Go version. |
| `3-14` | Eleven Pratt events: four calls with minimums 1, 5, 5, 6, and operator absorb/return decisions. |
| `15-20` | Five expression trees: subtraction, unary minus, comparisons, calls and explicit parentheses. |
| `21-29` | Recursive-descent choices for the chapter 3 statement, then its full program tree. |
| `30-31` | Function tree containing parameters, if/else blocks, and return statements. |
| `32-34` | Two first-error diagnostics, with line:column, expected token kinds and the found token. |
| `35-37` | Our tree and `go/parser.ParseExpr`'s tree in the same notation. |

Two-line output summary:
The trace records how successive subtraction operators return to the outer loop while multiplication is absorbed on the right.
Trees, statement choices, positioned errors, and a standard-library parse are printed in separate short sections.

No DOT figures are generated.
