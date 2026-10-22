# Learner Profile — Pratham

## Who

- 2nd-year CS student, aiming for infrastructure/systems engineering roles.
- Languages: Go (main), C, Python; learning Rust.

## Background

- **Comfortable with:** Linux namespaces, cgroups v2, OverlayFS, VFS, eBPF/CO-RE.
- **Has built:** an OCI container runtime, an eBPF process tracer, an interpreter, a crypto CLI.
- **Shakier on:** general C and Linux-internals fundamentals — "somewhat okayish," not solid. Don't assume them.
- **Theory, comfortable with** (self-check, 2026-10-16): set notation, equivalence
  relations, big-O including amortized analysis, two's complement arithmetic, vectors,
  matrices, matrix multiplication, numerical precision, basic calculus.
- **Theory, not yet known, or not taught in college yet:**
  - Proof and logic: proof by induction, including structural induction; statements with
    ∀, ∃ and implication.
  - Graph theory of any kind: paths, cycles, DAGs, trees, BFS/DFS, topological sort,
    strongly connected components, dominators, graph colouring, union-find, propagating
    values to a fixed point.
  - Automata and formal languages: DFAs and NFAs, limits of finite automata, pushdown
    automata, context-free grammars, ambiguity and left recursion, FIRST/FOLLOW, the
    Chomsky hierarchy.
  - Order theory: partial orders, lattices, monotone functions and fixed points.
  - Algorithms and computability: dynamic programming, NP-completeness and reductions,
    the halting problem and Rice's theorem.
  - Types: inference-rule notation, lambda calculus, unification, type soundness.
  - Low level: IEEE 754 floating point, bit-manipulation idioms, memory ordering and data
    races.
- **Main OS resource:** OSTEP.

## How I learn best

- Start in plain language, then build step by step to full intuitive technical depth.
- Most online material on topics like the eBPF verifier and compilers jumped in too technical for me.
- I'd rather be asked guiding questions than handed finished answers or code.

## Writing style I want

- Flowing, plain prose.
- **Avoid:** runs of short punchy sentences, content stuffed into parentheses, heavy semicolon use.
- No walls of text: structured, with the main point first.

## Progress

- **Compilers:** reinforce Lattner's M × N argument (a shared IR means M + N pieces: one front end per language, one back end per target) and that clang's LLVM IR is not target-neutral. Not yet quizzed from ch. 1: the idivq → #DE → SIGFPE chain, assembler/linker/driver boundaries, bootstrapping and trusting trust.
