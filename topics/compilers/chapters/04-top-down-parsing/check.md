Supported (unchanged paragraphs): 50; miscited: 1; stretched: 2; unsupported: 3; contradicted: 10; output mismatch: 1; misleading simplification: 6; stretched facts: 3.

Reviewed all 70 paragraph/claim blocks printed by `claims.py`, all four included diagrams, all four labs' recorded `run.out` files, the cited verbatim evidence, pitfalls, and roadmap. The supported count denotes unchanged paragraph blocks; findings count individual issues, so several can share a paragraph. Line numbers refer to `chapter.md` unless marked as facts.

| Line | Category | Change | Evidence |
|---|---|---|---|
| 19 | contradicted | Distinguished grammar terminal `num` from the lexer's actual `INT` token kind. | F1; `lab/parser/lexer.go:71–75` |
| 30 | misleading simplification | Explained that numeric token leaves are displayed using their text. | F4; `lab/grammar/main.py:69–77`; `lab/grammar/run.out:3–11` |
| 32 | contradicted | Allowed ε leaves, matching the later rewritten-grammar diagram. | `lab/grammar/main.py:238–241`; diagram included at chapter lines 113–114 |
| 32 | stretched | Required corresponding rewrite nodes, not merely the same collection of rules. | F5 in its example context; F6; `lab/grammar/run.out:3–27` |
| 94 | unsupported | Added primary-source evidence for top-down construction and the definition of left recursion. | New F62–F63 |
| 129 | misleading simplification | Restricted one-token production choice to this predictive parser, not every top-down parser. | F44; F62 |
| 133 | contradicted | Removed ε during propagation; added it only when the entire right side is nullable. | F40; new F64 |
| 135 | contradicted | Initialized only nonterminal FIRST sets empty; terminals start with themselves. | New F65; `lab/grammar/run.out:38–42` |
| 159 | unsupported | Added primary-source evidence for general FOLLOW propagation through nullable suffixes. | New F66; `lab/grammar/run.out:43–46` |
| 164, term definition | contradicted | Removed ε from the START term definition, matching its formula and table. | F38; `lab/grammar/run.out:48–55` |
| 164, FIRST+ sentence | contradicted | Distinguished the second edition's ε-retaining FIRST+ formula from third-edition START. | F38–F39 |
| 164, uniqueness sentence | contradicted | Changed exactly one production to at most one, allowing syntax-error cells. | F43; `lab/grammar/run.out:56–62` |
| 176 | contradicted | Restricted START-set containment to G2; retained the general LL(1) prohibition on left recursion. | F33; F38; `lab/grammar/run.out:63–67` |
| 178 | misleading simplification | Specified that the production's first symbol must end up on top of the stack. | `lab/grammar/main.py:158–174`; `lab/grammar/run.out:69–78` |
| 197 | output mismatch | Described choices, not every output line, as equivalent table lookups. | `lab/parser/run.out:22–29` includes a final tree line |
| 204 | misleading simplification | Replaced literally unbounded Go memory with nesting-dependent stack growth subject to the runtime limit. | F59–F60; `lab/left-recursion/run.out:3–6` |
| 206 | stretched | Limited the Go claim to the documented Expression production above `binaryExpr`. | F53; F54 |
| 221 | contradicted | Separated precedence from the `+ 1` mechanism that supplies left associativity. | `lab/parser/parser.go:67–85`; `lab/parser/run.out:4–14` |
| 226 | contradicted | Credited the parser, not the binary loop, with handling calls and parentheses. | `lab/parser/parser.go:96–112`; `lab/parser/run.out:16–20` |
| 231, term definition | misleading simplification | Allowed associativity-dependent right-operand minima, including the right-associative variant just explained. | F49; chapter line 226's derivation |
| 233 | miscited | Added direct evidence for Crockford's strict loop test and `expression(bp)` right operand. | F48–F49; new F68–F69 |
| 238 | misleading simplification | Scoped uniqueness to these expressions and included associativity alongside the precedence table. | F27–F29; F6; `lab/grammar/run.out:21–30` |
| 257 | unsupported | Verified and cited the standard term left factoring. | New F67 |
| facts F5 | stretched fact | Narrowed the claim to the textbook's displayed example rather than arbitrary derivations of one sentence. | F5 quote; S7 §3.2.3, printed p. 92 |
| facts F49 | stretched fact | Removed unquoted exact argument expressions from the claim; recorded implementation evidence separately. | F49 quote; new F69 |
| facts F53 | stretched fact | Replaced the universal claim about every grammar production with the quoted Expression example. | F53 quote |

The FIRST/FOLLOW pass traces, 35-addition termination bound, five groupings' arithmetic, Pratt trace, integer-threshold equivalence, self-test derivations, and generated diagram structures agree with their evidence. The Clarke report date remains 1985 as quoted in F51. No generated `out/` files, lab includes, term markers, or pre-check draft were removed or edited. Added eight facts (F62–F69) and narrowed three existing fact claims through `state.py`. No labs, tests, or render were run.

Human doubts: None remaining.
