Supported: 33 paragraphs; miscited: 1; stretched: 3; unsupported: 8; contradicted: 5; output mismatch: 2; misleading simplification: 12; stretched facts: 4.

Counts for supported material are paragraph-level; other counts are findings, including separately narrowed scout summaries. Lines refer to the original draft and remain unchanged in the fixed chapter.

| Line | Category | Changed or recommended | Evidence |
|---|---|---|---|
| 13, 58 | unsupported | Added Go and C evidence for the intended arithmetic grouping. | F13, F14, F51 |
| 23 | unsupported | Cited the limitation of regular expressions and finite-state recognizers. | F48 |
| 23 | misleading simplification | Limited the call-stack explanation to recursive descent, not all parsers. | F50; grammar-lab/run.out:57–80 |
| 25 | unsupported | Cited production rewriting and the designated start symbol. | F2, F49 |
| 37 | contradicted | Inserted the missing single-nonterminal rewrite in the leftmost derivation. | F2, F3; chapter.md:30–32 |
| 41 | stretched | Changed “introduced context-free rules” to distinguishing generative rules from transformations. | F10 |
| 41 | unsupported | Removed the unnecessary ALGOL expansion; restored IAL and the cited 1963 naming date. | F9; [archived report title](https://archive.computerhistory.org/resources/text/algol/algol_bulletin/EX/RR60/INDEX.HTM) |
| 58, 215 | misleading simplification | Limited different meanings to this example; allowed intentional disambiguation outside the grammar. | F6, F12–F16; grammar-lab/run.out:4–9 |
| 76 | contradicted | Qualified precedence layering for parentheses, which can put subtraction below multiplication. | chapter.md:71–73; derivable counterexample `(10 - 4) * 3` |
| 76 | contradicted | Removed same-language guarantee when changing only the subtraction alternative to right recursion. | chapter.md:71–73; `num + num - num` fails the partially changed grammar |
| 78 | misleading simplification | Limited function-per-nonterminal behavior to naive recursive descent. | F27, F50; grammar-lab/run.out:57–80 |
| 90 | misleading simplification | Added the indirect-recursion algorithm's no-cycle and no-ε-production assumptions. | F20; S7 §3.3.1, printed p. 104, PDF p. 131 |
| F20 claim | stretched fact | Narrowed the scout summary to grammars satisfying the algorithm's assumptions. | S7 §3.3.1, printed p. 104, PDF p. 131 |
| 95 | output mismatch | Included both `+ T` and `- T`; identified the loop as subtraction-only. | grammar-lab/run.out:24–25; left-recursion/main.go:30–38 |
| 95, 208, 216 | misleading simplification | Distinguished a right-recursive tail from an already grouped binary operator tree. | F19; grammar-lab/run.out:24–25; rewritten `S` productions |
| 101 | misleading simplification | Declared the lab's separate-nullable convention instead of silently omitting ε from FIRST. | F21; grammar-lab/NOTES.md:5; S7 §3.3.1, printed p. 107 |
| 108 | miscited | Cited the START naming passage rather than only its disjointness condition. | F52 replaces F23 for naming |
| 108 | misleading simplification | Clarified that the lab's FIRST+ excludes ε, unlike the quoted second-edition formula. | F24; grammar-lab/run.out:37–44; S7 §3.3.1, printed pp. 110–111 |
| 113 | misleading simplification | Scoped the disjointness test to one-token prediction; clarified LL(1)'s predictive requirement. | F23, F25; S7 §3.3.1, printed p. 106 |
| 134 | misleading simplification | Broadened recursive-descent definition beyond predictive production selection and added evidence. | F50; S7 §3.3.2 |
| 138 | unsupported | Removed the unspecified comparison with a “C-like language.” | F13 supports Go's five levels, not the unspecified language |
| 140 | misleading simplification | Broadened Pratt definition to include prefix and continuation behavior, including suffix operators. | F31, F53; parser/parser.go:81–85 |
| 140 | unsupported | Added evidence explicitly expanding nud and led. | F53 |
| F31 claim | stretched fact | Removed acronym expansions absent from this quote; retained them under new evidence. | F31, F53 |
| 153 | misleading simplification | Used `power` for this loop's right associativity; distinguished Crockford's strict comparison. | F34, F35; parser/parser.go:72–85 |
| 164 | unsupported | Removed the unsourced claim that obscurity lasted decades. | F33 establishes scarce contemporary articles, not a decades-long history |
| 164 | stretched | Replaced an unsupported revival claim with Crockford's documented book contribution. | F32 |
| 164 | stretched | Described the scanner's precedence field rather than precedence attached to every token. | F39 |
| F39 claim | stretched fact | Narrowed the scout summary to the declared fields and valid token kinds. | F39 |
| F38 claim | stretched fact | Removed “recursive,” which the quoted function opening does not demonstrate. | F38 |
| 196 | output mismatch | Specified matching trees, not identical complete output lines. | parser/run.out:11,29 |
| 199 | contradicted | Added lexer support for `%` to the exercise prerequisites. | parser/main.go:84–87; parser/parser.go:57–60 |
| 202 | unsupported | Cited recovery, left-recursion support, and Bison's bottom-up algorithm; avoided an all-grammars guarantee. | F54–F57; [Bison recursion manual](https://web.mit.edu/gnu/doc/html/bison_6.html); [Bison algorithm manual](https://web.mit.edu/gnu/doc/html/bison_8.html) |
| 207 | contradicted | Restricted equal-language comparison to numbers, subtraction and multiplication, without parentheses. | chapter.md:30–32,71–73; layered grammar additionally accepts `id`, `+`, `/`, parentheses |
| 219 | misleading simplification | Added the FOLLOW check needed to avoid a conflict after left factoring. | F22, F23, F26; FIRST of `( Args )` versus FOLLOW of `E'` |

Read the initial claims listing, all three captured lab outputs and NOTES files, roadmap, pitfalls, and relevant implementation excerpts. Added F48–F57 and narrowed F20, F31, F38 and F39. No labs, lint, render, or other post-edit checks were run. Main should run chapter lint and render; unchanged labs need not be rerun solely for these prose corrections.

## Human doubts

- Historical attributions in F9/F10 still rely on Wikipedia quotes; a primary historical review would strengthen them.
- Bison evidence comes from an older GNU manual mirrored at MIT; current upstream manual fetches timed out.
