# Grammar lab

Run from the repository root:

`python3 tools/lab.py run topics/compilers/chapters/04-top-down-parsing --only grammar`

The program computes the trees, direct-left-recursion elimination, FIRST/FOLLOW fixed
points, START sets, and predictive tables. Set display order and production order are
explicit. FIRST/FOLLOW update in place; the last printed pass changes nothing.
`num` is the token kind; derivation frontiers and tree leaves show its concrete lexeme.

## Source excerpts

Each range below is at most 25 lines. Prefer the derivation and sequence-FIRST cores for
chapter code; the remaining ranges are alternatives or implementation references, not a
request to include them all.

- `main.py:69-77`: rewrite the leftmost nonterminal once per line.
- `main.py:94-103`: FIRST of a sequence, including nullable prefixes.
- `main.py:80-91`: direct-left-recursion elimination that actually produces G3.
- `main.py:52-66`: parentheses and values computed from tree structure.
- `main.py:111-135`: fixed-point updates, including in-place FOLLOW propagation.
- `main.py:141-155`: production numbering, START construction, table insertion.
- `main.py:158-174`: predictive parser with explicit stack, input, action.
- `main.py:177-184`: DOT node/edge emission from actual tree objects.

## Output sections

Every proposed output include is at most 20 lines.

| `run.out` | Observation |
| --- | --- |
| `1-2` | Python version. |
| `3-11` | Leftmost derivation for the tree valued 0; one rewrite per line. |
| `12-20` | Leftmost derivation for the tree valued 6; the first rewrite uses multiplication. |
| `21-27` | All five fully parenthesized trees, their values, and the computed count. |
| `28-30` | G2 yields one tree, with value 0. |
| `31-36` | G3 as produced by eliminating direct left recursion from G2. |
| `37-42` | FIRST grows across four in-place passes, including the unchanged pass. |
| `43-46` | FOLLOW grows across three in-place passes, including the unchanged pass. |
| `47-55` | Eight numbered G3 productions and their computed START sets. |
| `56-62` | G3 predictive table, with `.` for an empty cell. |
| `63-67` | G2 cells containing two numbered productions. |
| `68-78` | Header plus the first ten predictive-parse steps, stack top at the left. |
| `79-91` | Remaining predictive-parse steps, ending in `accept`. |

A two-part summary: the derivations and enumerated trees expose five values for one
input, followed by one layered tree. The computed sets produce G3's single-entry table,
G2's multi-entry cells, and the explicit predictive-parse steps.

## Generated figures

- `out/tree-0.dot`: G1 tree rooted at subtraction, with `10 - 4` and `3 * 2` subtrees.
- `out/tree-6.dot`: G1 tree rooted at multiplication, with `((10 - 4) - 3)` on the left.
- `out/layered.dot`: full G2 tree, retaining Expr, Term, Factor and terminal nodes.
- `out/rewritten.dot`: subtraction-only right-leaning E/E' parse tree for `10 - 4 - 3`,
  beside the left-folded operator tree. The empty tail has an explicit ε child.

`run.sh` runs Graphviz `dot -Tsvg` for every DOT file when `dot` is installed, writing
corresponding SVGs under `out/`. No colors or fonts are specified; `ordering=out` retains
child order. The figures are grammar trees, not machine-state figures.
