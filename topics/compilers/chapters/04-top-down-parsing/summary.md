# Chapter 4 summary — Grammars and top-down parsing

The reader now knows a token list has no structure: `10 - 4 - 3 * 2` groups five ways (6, 18, 0, 8, 12). He can define a context-free grammar (terminals are chapter 3's token kinds, `num` for `INT`), trace a leftmost derivation one rewrite at a time, and read a parse tree, whose root operator is applied last. `E → ( E )` answers chapter 3's balanced-parentheses limit. He saw both drawn trees (worth 0 and 6) for the ambiguous `E → E - E | E * E | ( E ) | num`, the dangling else (C: nearest-`if` rule; Go: mandatory braces), Go's EBNF, and BNF's origin.

The layered Expr/Term/Factor grammar encodes precedence by levels and left associativity by left recursion, as C's standard does. Go pairs an ambiguous `Expression` production with a five-level table. Precedence is not evaluation order: Go calls `f`, `g`, `h` left to right. A recursive-descent function written straight from a left-recursive rule hit the 1 GB goroutine stack limit. Removing left recursion keeps the language but leans the tree right, so a loop folds it back left.

He computed FIRST (ε marker) and FOLLOW (`eof`) by hand in repeated passes until nothing changed (a fixed point), then START sets (FIRST+ in the 2nd edition), the backtrack-free LL(1) condition, G3's table, G2's four conflicts, and a table-driven parse. The lab's `parseStmt` `switch` is one table row. Pratt parsing: nud/led, binding powers (`-` 4, `*` 5), a hand trace with minimums 1, 5, 5, 6, prefix minus at 6. `exprc`'s loop is precedence climbing, the same algorithm, and `go/parser` builds the same tree.

Open threads: LR parsing, error recovery and hand-written parsers (ch. 5), ASTs and scopes (ch. 6), fixed points in dataflow (ch. 11). Left factoring appears only in a self-test.
