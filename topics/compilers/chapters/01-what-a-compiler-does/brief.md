# Chapter 1 — What a compiler actually does

## 1. Starting point

The reader is Pratham, a 2nd-year CS student whose main language is Go, who also writes C
and Python and is learning Rust. He has built an OCI container runtime, an eBPF process
tracer, a crypto CLI and, most relevant here, a tree-walking interpreter. This is the
**first chapter of the topic**, so there are no earlier summaries, no known chapters, and
the glossary is empty. Assume only what the profile and the chapter prereqs grant:

- He can read and write Go comfortably, and has written a lexer, a parser and an evaluator
  that walks an AST. Words like "token", "parser" and "AST" can be used, with one short
  reminder each, but "IR", "back end", "assembler", "linker" and "JIT" must be introduced.
- He has **no assembly background**. Chapter 2 teaches the machine properly. This chapter
  may show a few x86-64 instructions, but must explain each one it shows in plain words
  and must not lean on calling-convention detail.
- He is shakier on C and Linux fundamentals, so the toolchain steps (`as`, `ld`, the `gcc`
  driver) need a gentle walk-through rather than a nod.

Connections to make explicitly: the reader's interpreter is the anchor of the whole
chapter. The tiny compiler should walk the **same kind of AST** his evaluator walks, with
the one change that each node *emits instructions* instead of *computing a value*. That
single contrast is the chapter's best teaching move. Plant seeds for later chapters by
name: chapter 2 (the machine and the stack), chapters 3 to 6 (the front end this chapter
waves past), chapter 10 onward (IRs), chapters 18 to 20 (the back end), chapter 22 (JITs).

## 2. Crux

**When you "compile" a program, what actually happens between the source text and the
bytes the CPU runs, and how is that different from what your interpreter already does?**

## 3. Opening situation

Pratham's interpreter can evaluate `(7 + 5) * 3 - 6` and print `30`. Every time it runs,
it re-reads the text, rebuilds the tree, and walks it, and the Go program doing the walking
has to be present on the machine. Now he types `go build` on that same interpreter and gets
a single file that runs on a machine with no Go installed at all. Something turned Go text
into instructions an x86-64 CPU executes directly. What did it produce, in what steps, and
could he write one himself for his own little expression language? By the end of the
chapter he has: a Go program that turns `(7 + 5) * 3 - 6` into an assembly file, which
`gcc` turns into an executable that prints `30`, with no interpreter in sight.

## 4. Sections

Budgets sum to 3200, inside the chapter's 2500 to 3500 range.

1. **Two ways to run a program** (~550 words)
   An interpreter executes the program; a compiler translates it into another language and
   must preserve its meaning. Use the reader's interpreter as the example of the first and
   frame the second as "the same tree walk, but writing down what to do instead of doing
   it". State the property that defines correctness of a compiler: the translated program
   behaves the same as the original. Note that "compiled" and "interpreted" describe
   implementations, not languages. Ground in S7 (definitions), S1 for framing.

2. **A spectrum, not two boxes** (~450 words)
   Ahead-of-time compilation to machine code (Go, C), compilation to bytecode run by a
   virtual machine (CPython, the JVM), and just-in-time compilation that compiles hot code
   while the program runs (HotSpot, V8, CPython 3.13's experimental JIT). Most real systems
   mix these. Keep it short; chapter 22 returns to JITs. Ground in S29, S28, and whatever
   the scouts find for CPython's bytecode and the JVM.

3. **Inside the pipeline** (~600 words)
   Front end (understand the source: lex, parse, check), middle end (improve a
   language- and machine-neutral IR), back end (choose instructions and registers for one
   target). Use the Go compiler's own phase list as the real example (S30). Explain the
   M languages times N targets argument with LLVM as the case where it paid off (S14 plus
   the scouts' LLVM source). Show the `pipeline-peek` lab: one small C function seen as
   LLVM IR, then lowered by the same `llc` into two different targets' assembly, so the
   reader sees the shared middle and the swapped back end. Mention that a toolchain is
   more than the compiler: the assembler and linker finish the job, and `gcc` as a driver
   hides them.

4. **A compiler you can hold in your head** (~1000 words)
   The heart of the chapter, built around the `exprc` lab. Walk through it in steps: reuse
   an interpreter-style lexer and parser (wave past it, chapters 3 to 5 cover it properly),
   then the code generator: a recursive function over the AST that emits stack-machine
   style x86-64 (push each operand, pop two, operate, push the result). Explain each
   instruction shown in plain words. Show the generated `.s` for the running example, the
   small C driver that calls it and prints the result (Ghuloum's approach in S1), the
   `gcc` command that assembles and links, and the run printing `30`. Close with one
   honest edge: division by zero is a run-time event in the compiled program, not a
   compile-time error, and the lab shows what happens. Pose guiding questions to the
   reader at key moments ("what should the code for a single number be?") before showing
   the answer. Ground in S1, S2 (only for the return register and alignment if mentioned),
   and scout facts on the instructions used.

5. **The compiler that compiles itself** (~450 words)
   Bootstrapping: how a compiler written in its own language comes to exist (an earlier
   compiler, often in another language, builds the first version; from then on each
   release is built by an older one). Real cases: the Go toolchain's move from C to Go in
   Go 1.5 and its current bootstrap-version requirement; rustc's stage0, stage1, stage2
   build. One paragraph on Thompson's "Reflections on Trusting Trust" as the consequence:
   you are trusting the binary that built your compiler. Ground in scout facts.

6. **What you now have, and what is missing** (~150 words)
   The tiny compiler skipped almost everything a real one does: no types, no variables, no
   IR, no optimization, no registers beyond what the stack trick needs. Map each gap to the
   part of the book that fills it. No new facts here.

## 5. Running example

The expression `(7 + 5) * 3 - 6`, which evaluates to `30`. It appears in the opening (the
interpreter evaluating it), in section 1 (the tree, walked two ways), in section 4 (its
generated assembly and the run), and in section 6. Its tree has all three binary
operators the code generator needs to handle besides division, and the parentheses force
the tree to differ from plain left-to-right reading. Division is shown separately as the
edge case.

## 6. New terms

compiler, interpreter, source language and target language, ahead-of-time (AOT)
compilation, bytecode, virtual machine (language VM, not a hypervisor VM), just-in-time
(JIT) compilation, front end, middle end, back end, intermediate representation (IR),
assembly language, assembler, object file, linker, compiler driver, stack-machine code
generation, bootstrapping, self-hosting compiler.

Excluded as already known from building an interpreter: token, lexer, parser, AST.

## 7. Misconceptions

1. **"Compiled or interpreted is a property of the language."** It is a property of an
   implementation: Python has CPython's bytecode interpreter and a JIT, and C has
   interpreters. Section 1 and 2 should leave the reader saying "this implementation
   compiles to X".
2. **"The compiler produces the executable."** The compiler proper emits assembly (or an
   object file). The assembler and linker finish the job, and `gcc` or `go build` runs all
   of them as a driver. The `exprc` lab makes this visible, because the reader's compiler
   only writes a `.s` file.

## 8. Fact questions

### Batch 1 — Definitions and the execution spectrum (suggest S7, S29, S28; may search)

1. How does *Engineering a Compiler* (S7) define a compiler, and how does it define an
   interpreter? Quote the definitions if available.
2. What does CPython compile source code to before executing it, and what executes that
   form? (Official CPython docs, e.g. the `dis` module or the glossary entry for
   "bytecode".)
3. In CPython 3.13, is the JIT described in PEP 744 enabled by default, and how is it
   turned on at build time? What tiers does PEP 744 describe beneath it (specializing
   adaptive interpreter, micro-ops)?
4. What technique does the CPython 3.13 JIT use (copy-and-patch, per PEP 744 and S28), in
   one precise sentence?
5. What does `javac` produce, and what does the HotSpot JVM do with frequently executed
   code? (Official Oracle or OpenJDK documentation.)

### Batch 2 — The pipeline, IRs and the M×N argument (suggest S30, S14; may search)

6. What phases does the Go compiler's own README (S30, go1.23.0) list, in order, and under
   what names (for example parsing, type checking, IR construction, middle end, walk,
   generic SSA, machine code generation)?
7. Which packages under `cmd/compile/internal` does that README name for parsing, type
   checking, and SSA?
8. Where does Chris Lattner's LLVM chapter in *The Architecture of Open Source
   Applications* make the argument about supporting N source languages and M targets
   with a shared optimizer, and what exactly does it say? (Search for that chapter; add it
   as a new source.)
9. What three forms does LLVM IR come in, according to the LLVM Language Reference (S14)?
10. What are the names of GCC's main intermediate representations (GENERIC, GIMPLE,
    RTL), per the GCC internals manual?

### Batch 3 — The tiny compiler's machine code (suggest S1, S2; may search for GNU as and Intel SDM)

11. In Ghuloum's paper (S1), how is compiled code started and its result printed (a C
    runtime calling a function such as `scheme_entry`), and what is the paper's claim
    about every incremental step producing a working compiler?
12. In the System V AMD64 ABI (S2), which register holds an integer return value, and
    what stack alignment is required at a `call` instruction?
13. What exactly do `push` and `pop` do to `%rsp` and memory on x86-64 (8-byte operands)?
14. What do `cqo` (AT&T `cqto`) and `idiv` do: which registers hold the dividend,
    quotient and remainder, and what happens on division by zero or on
    `INT64_MIN / -1`? Which signal does Linux deliver for that exception?
15. What syntax does the GNU assembler use by default for x86-64 (AT&T), and which way do
    operands go in AT&T syntax?

### Batch 4 — Bootstrapping and trust (may search; prefer go.dev, rustc-dev-guide, ACM)

16. In which release did the Go toolchain stop containing C, and how was the compiler
    converted from C to Go (the Go 1.5 release notes)?
17. What Go version is currently required to bootstrap building Go from source, according
    to go.dev's "Installing Go from source" page, and what is the general bootstrap
    version policy?
18. What are rustc's bootstrap stages (stage0, stage1, stage2), and what compiler is each
    built with, according to the rustc-dev-guide's bootstrapping chapter?
19. What does Ken Thompson's 1984 Turing Award lecture "Reflections on Trusting Trust"
    demonstrate, and what is its stated moral?

## 9. Lab plan

Runner `local` for both. Toolchains from the profile: go, gcc, clang, llc.

1. **`exprc`** — the chapter's tiny compiler, and the seed of the book-long Go compiler.
   - Demonstrates: a Go program with a minimal lexer, a recursive-descent parser for
     `+ - * /` and parentheses with the usual precedence, and a code generator that walks
     the AST and writes stack-machine style x86-64 AT&T assembly for a function (for
     example `compute`) that returns the result in `%rax`. A small C driver calls it and
     prints the result, in the style of Ghuloum's `scheme_entry`. `gcc` assembles and
     links.
   - Run: compile `(7 + 5) * 3 - 6`, `cat` the generated `.s`, build it with `gcc`, and
     run it, printing `30`. Then compile `10 / (5 - 5)` and run it, showing that the
     compiled program dies at run time (expected SIGFPE from `idiv`) while the compiler
     itself succeeded. Also show, in a line or two, that the reader's compiler wrote only
     a `.s` file, and that `gcc` produced the object file and executable.
   - Expected result: `success` for the lab as a whole (the division case is expected
     run-time death inside a step the lab script anticipates and reports, for example by
     printing the exit status).
   - Output should make visible: the generated assembly for the running example, short
     enough to quote whole; the printed `30`; the division failure with its signal or
     exit status.
   - Keep the Go code small and readable (well under 200 lines total), structured as
     lexer, parser, codegen, so later chapters can replace each phase.

2. **`pipeline-peek`** — the pipeline and the M×N split made visible.
   - Demonstrates: one small C function (for example `int f(int x) { return (x + 5) * 3
     - 6; }`) taken to LLVM IR with `clang -S -emit-llvm -O1` (or `-O0` plus a note), then
     the same `.ll` file lowered by `llc` to x86-64 and to one other target such as
     AArch64 or RISC-V, if this `llc` has that target registered. If no second target is
     available, show `llc --version` registered targets and use x86-64 only, reporting
     that.
   - Expected result: `success`.
   - Output should make visible: the short IR for `f`, and the two assembly listings side
     by side or one after the other, short enough to quote, so the reader sees one IR and
     two back ends.
