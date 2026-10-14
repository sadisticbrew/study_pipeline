# Grammar lab

Run from the repository root with `python3 tools/lab.py run topics/compilers/chapters/04-top-down-parsing --only grammar-lab`.

The ambiguity enumerator tries every binary split of the fixed token sequence, preserving token order. The set computation iterates to a fixed point. FIRST contains terminals only; epsilon is represented by the separate nullable set. The rewrite mechanically removes direct left recursion from the supplied layered grammar, not indirect recursion in arbitrary grammars. `$` is end of input. The full table prints all populated cells; omitted cells reject input. Input numbers are mapped to the grammar terminal `num` for the predictive trace. Stack top is printed at the left.

## Source excerpts

Paths are relative to this lab directory. Each suggested include is at most 25 lines.

- `grammar.py:4-16`: enumerate all binary trees and evaluate each grouping.
- `grammar.py:19-29`: direct-left-recursion rewrite.
- `grammar.py:38-55`: FIRST of a sequence, nullable and FIRST fixed point.
- `grammar.py:56-77`: FOLLOW fixed point and FIRST+ table construction.
- `grammar.py:95-113`: table-driven predictive parser.

## Output excerpts

- `run.out:1-2`: Python version.
- `run.out:3-9`: five fully parenthesized trees, values 12, 8, 0, 18 and 6, and tree count.
- `run.out:11-21`: original nullable, FIRST and FOLLOW sets, followed by all six conflicting table cells.
- `run.out:23-28`: mechanically rewritten productions, including epsilon tails.
- `run.out:30-36`: rewritten nullable, FIRST and FOLLOW sets.
- `run.out:37-47`: FIRST+ for every rewritten production.
- `run.out:49-55`: full populated LL(1) table and observed conflicting-cell count 0.
- `run.out:57-80`: full trace; quote `57-64` for the first expansion, match and epsilon choice, or `69-80` for the second subtraction, multiplication and final accept. Do not include all 24 trace lines in one chapter block.

The captured run enumerates five trees and prints six conflicting cells for the left-recursive grammar.
The rewritten table has zero conflicting cells, and its predictive trace ends with `$ | $ | accept`.
