# Real lexer lab

Run from the repository root with `python3 tools/lab.py run topics/compilers/chapters/03-lexing --only real-lexers`.

The lab uses installed Go, flex and gcc. Generated C and executables live in `/tmp`, not in the source directory. The two flex specifications differ only in the ordering of the keyword and identifier rules. The five running rules are supplemented by punctuation and trivia so the entire opening line can be scanned. Neither C example is executed; gcc only checks syntax. The script requires rejection of `munch.c` and acceptance of `spaced.c`, while keeping the lab's expected result success.

## Source excerpts

Paths are relative to this lab directory; every suggested excerpt is at most 25 lines.

- `scanner.go:9-22`: go/scanner input, scan loop and literal printing.
- `tokens.l:5-16`: keyword-first rules and driver.
- `swapped.l:5-16`: identifier-first rules and driver.
- `munch.c:1-3` and `spaced.c:1-3`: the two C expressions.
- `run.sh:18-27`: expected gcc rejection and clean syntax check, with captured exit statuses.

## Output excerpts

- `run.out:1-4`: Go 1.27.1-X:nodwarf5, flex 2.6.4 and gcc 16.2.1.
- `run.out:6-20`: source and scanner tokens. Inserted semicolons have literal `"\n"` at 1:7, 2:4 and 3:5, following an integer, `++` and `)` respectively. Scanner EOF is reported at 3:6.
- `run.out:22-23`: keyword-first flex emits IF(if) followed by the opening line's other nontrivia tokens.
- `run.out:25-27`: swapped rules produce `swapped.l:7: warning, rule cannot be matched`; output begins IDENT(if).
- `run.out:29-34`: gcc reports `munch.c:2:15: error: lvalue required as increment operand` and exits 1 for `x+++++y`. The actual diagnostic and source caret are retained, not replaced by a summary.
- `run.out:36-37`: the spaced `x++ + ++y` case has no diagnostic and exits 0.

The gcc diagnostic alone is not a token dump; the chapter must explain maximal munch from its language source rather than present the diagnostic as proof of every token boundary.
