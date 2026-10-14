# Book parser lab

Run from the repository root with `python3 tools/lab.py run topics/compilers/chapters/04-top-down-parsing --only parser`.

`main.go` is copied unchanged from chapter 3's `lab/lexer/main.go`. `parser.go` adds recursive-descent statements and Pratt expressions; `driver.go` prints observations. `compare.go` is a separate executable using the standard Go parser for the running expression. `run.sh` supplies explicit file lists so the two entry points do not conflict.

The book's comparison operators share binding power 10, addition/subtraction 20, multiplication/division 30. All binary operators group left through the right-hand minimum `power + 1`. Prefix minus parses with minimum 40; calls bind at 50. Functions have untyped identifier parameters; variables may have an initializer. `if` and `else` bodies require braces. Ordinary statements require explicit `;` between them; braced statements are self-delimiting, and a final statement before `}` or EOF needs no separator. There is no Go semicolon insertion. Parse functions return the first positioned error rather than panic or recover. S-expressions describe syntax only: no type checking is performed on `a < b == c`.

## Source excerpts

Paths are relative to this lab directory. Suggested includes stay within the chapter's 25-line limit.

- `parser.go:39-54`: positioned first error and expected-token helper.
- `parser.go:56-60`: binding-power table.
- `parser.go:63-89`: complete Pratt loop, 27 lines (under the requested 40-line core target). For chapter blocks split into `63-80` (lookahead and trace decisions) and `81-89` (call/infix dispatch and right-hand minimum).
- `parser.go:91-109`: integers, names, prefix minus and parentheses.
- `parser.go:110-123`: call arguments.
- `parser.go:172-187`: recursive descent for braced `if`/`else` and `return`.
- `parser.go:201-219`: function declarations and parameters.
- `compare.go:10-27`: standard Go AST formatting and `go/parser.ParseExpr`.
- `main.go:43-60` or `61-83`: unchanged chapter 3 lexer, if needed; prefer linking to chapter 3 rather than re-quoting it.

## Output excerpts

- `run.out:1-2`: Go version.
- `run.out:3-8`: Pratt trace with operator power, current minimum and absorb/return decision, then the resulting tree.
- `run.out:10-14`: requested expression trees, showing left-fold subtraction, nested multiplication, prefix minus, comparison grouping and calls.
- `run.out:16-18`: braced assignment and a function with parameters, `if`/`else` and returns.
- `run.out:20-22`: remaining comparison/division operators, parentheses, variable declarations, separators, expression statements and a standalone block.
- `run.out:24-26`: missing `)` at 1:11 and missing expression at 1:12, both reported without a panic.
- `run.out:28-29`: standard Go parser's tree; compare with lines 8 or 11.

The Pratt trace returns on the second minus at minimum 21, then absorbs multiplication at that minimum.
The output includes all requested trees and positioned errors, and `go/parser` prints the same tree for the running expression.
