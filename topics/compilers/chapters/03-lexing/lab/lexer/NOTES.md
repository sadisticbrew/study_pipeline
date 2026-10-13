# Hand-written lexer lab

Run from the repository root with `python3 tools/lab.py run topics/compilers/chapters/03-lexing --only lexer`.

`main.go` contains the reusable lexer (91 lines); `driver.go` contains only observation printing. Token kinds are IDENT, INT, ERROR, EOF, keyword spelling, or punctuation spelling. Identifiers use ASCII letters and underscore followed by ASCII letters, underscore or digits. Decimal integers are unsigned digit runs; minus is its own token. Columns count decoded characters, with tabs counting as one column. Unexpected characters produce one ERROR token and scanning continues. EOF is repeatable. No Go-specific semicolon insertion is applied to the book's language.

## Source excerpts

Paths are relative to this lab directory; each suggested excerpt is at most 25 lines.

- `main.go:14-30`: keyword table, identifier predicates and lookahead.
- `main.go:43-60`: trivia skipping, saved position and EOF.
- `main.go:61-83`: core switch for identifiers, numbers and optional `=` lookahead.
- `main.go:76-91`: operators, punctuation and error recovery.
- `driver.go:17-29`: opening line and the six requested edge-case inputs.

## Output excerpts

- `run.out:1-2`: Go version.
- `run.out:3-15`: opening-line tokens and positions. `<=` starts at 1:7, the comment emits no token, and EOF is at 1:35.
- `run.out:17-23`: all six requested edge cases. `iffy` is IDENT at 1:1, `if` is keyword at 1:6, `a<=b` contains one `<=`, `a< =b` contains separate `<` and `=`, `x==y=z` contains `==` then `=`, and `10/2//c` contains division but no comment token. `x @ y` produces ERROR("@") at 1:3 and then IDENT("y") at 1:5.
- `run.out:25-28`: remaining token kinds, newline positions (the second identifier is at 2:3), and unexpected `!`, non-ASCII `é`, and NUL as ERROR tokens. These supplementary observations keep all supported operator/keyword paths visible.
