# Evaluation-order lab

Run from the repository root:

`python3 tools/lab.py run topics/compilers/chapters/04-top-down-parsing --only eval-order`

## Source excerpt

- `main.go:5-12` (8 lines): three observable function calls inside `f() - g() * h()`.

## Output sections

- `run.out:1-2`: Go version.
- `run.out:3-7`: the expression header, calls in order f, g, h, then value 4.

Two-line output summary:
The program prints `f`, `g`, `h` in that order.
The expression's printed value is 4.

No DOT figures are generated.
