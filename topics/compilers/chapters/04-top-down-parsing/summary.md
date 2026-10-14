# Chapter 4 summary — Grammars and top-down parsing

The reader now knows why parsing needs more than regular expressions: a rule that mentions itself can nest without bound, and in a hand-written parser the call stack holds that memory. He knows a context-free grammar's four parts (terminals, nonterminals, productions, start symbol), derivations, leftmost derivations, sentential forms and parse trees, plus BNF's history (Chomsky 1956, Backus for IAL/ALGOL 58, Naur's ALGOL 60 report) and the Go spec's EBNF.

He saw ambiguity concretely: `E → E - E | E * E | num` gives `10 - 4 - 3 * 2` five trees worth 12, 8, 0, 18 and 6. Ambiguity is undecidable in general, so designers avoid it by construction. He knows the dangling else, C's "nearest preceding if" rule, and Go's mandatory braces.

He separates precedence (layering `E`/`T`/`F`) from associativity (side of recursion), knows left recursion crashes naive recursive descent (the lab's lowered 32 KiB stack; Go's default is 1 GB), and the `A → β A'` rewrite, whose right-recursive tail a loop must fold back left. He can compute FIRST, nullable, FOLLOW and per-production lookahead sets (FIRST+ in EaC 2nd ed., START in 3rd), state the LL(1) condition, and knows left-recursive grammars are never LL(k), LL(k) grammars are unambiguous, and left factoring.

Pratt parsing: binding powers, nud/led, `power + 1` for left associativity. `exprc`'s precedence climbing is the same algorithm. Go, GCC (since 3.4/4.1), clang and rustc hand-write recursive-descent parsers.

Open threads: error recovery and bottom-up LR parsing (ch. 5), ASTs with positions and scopes (ch. 6).
