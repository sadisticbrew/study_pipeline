# Chapter 2 — The machine you compile to

## 1. Starting point

The reader is Pratham, a 2nd-year CS student whose main language is Go, who also writes C
and Python and is learning Rust. He has built a tree-walking interpreter, an OCI container
runtime and an eBPF tracer. He is shakier on C and Linux fundamentals, so nothing about
how C code becomes machine code can be assumed. He has **no assembly background beyond
chapter 1**.

From chapter 1 he knows:

- Compiler versus interpreter, the front/middle/back-end split, IR, assembler, object
  file, linker, compiler driver (all in the glossary, do not redefine them).
- `exprc`, his own Go compiler for arithmetic, which emits stack-machine x86-64 in AT&T
  syntax. He has seen exactly these instructions, each explained once: `movabsq`,
  `pushq`, `popq`, `addq`, `subq`, `imulq`, `cqto`, `idivq`, `ret`. He knows `pushq`
  moves `%rsp` down by 8 and stores, `popq` loads and moves it up by 8, and that the
  System V convention returns a 64-bit integer in `%rax`. He saw `10 / (5 - 5)` die with
  SIGFPE.
- "Register" is in the glossary only as "a small, very fast storage slot inside the
  processor". This chapter makes that concrete.

Connections to make explicitly:

- `exprc`'s `compute` is the anchor. It worked because it obeyed rules it never stated:
  result in `%rax`, stack left exactly as it found it, no callee-saved register touched,
  `ret` back to whoever called. This chapter names those rules. Ask the reader early:
  "why did `compute` work when called from C, and what would it have to do differently
  if it took an argument or called `printf`?"
- His interpreter: a recursive `eval` call in Go gets its own locals for free. Here he
  sees what "for free" costs: a frame on the machine stack, built by the callee.
- He is a Go programmer, so mention that Go's own compiler uses its own internal
  register-based calling convention rather than System V, which is why calling C from Go
  goes through cgo. One paragraph, grounded in scout facts, no more.
- Seeds by name: chapter 9 (compiling high-level features: closures, objects), chapter
  18 (instruction selection), chapter 19 (register allocation, which is where
  caller- vs callee-saved really matters), chapter 20 (object files, linking, loading),
  chapter 21 (runtimes, unwinding), chapter 22 (JITs writing machine code).

## 2. Crux

**What does the machine a compiler targets actually provide — registers, memory, a stack
and a handful of instruction kinds — and what rules must generated code follow so that
functions, including recursive ones and ones built by other compilers, can call each
other correctly?**

## 3. Opening situation

`exprc` compiled `(7 + 5) * 3 - 6`, a C driver called `compute`, and it printed `30`. Now
Pratham wants his language to have functions: `fact(n)` that calls `fact(n - 1)`. Three
questions appear at once that his stack-machine trick never had to answer. Where does `n`
live while the inner call runs, given that the inner call has its own `n`? How does the
inner call know where to come back to? And if his generated code calls a C function like
`printf`, which registers will still hold his values afterward, and what does `printf`
expect to find on the stack? The machine answers none of these by itself. A written
agreement, the calling convention, answers them, and every compiler on the system follows
it. By the end of the chapter he can read `gcc`'s output for a recursive `fact`, point at
each frame, and write an assembly function that C can call.

## 4. Sections

Budgets sum to 3200, inside the chapter's 2500 to 3500 range.

1. **What the processor gives you** (~450 words)
   Plain-language model first: memory as a huge array of bytes indexed by address; the
   processor holds a few registers and an instruction pointer, fetches the instruction at
   `%rip`, does it, moves on. Then the concrete x86-64 facts: sixteen 64-bit
   general-purpose registers and their names, the narrower names for their low parts
   (`%eax`, `%ax`, `%al`), the rule that writing a 32-bit register zeroes the upper 32
   bits, little-endian byte order, and the flags register set by arithmetic and compares.
   Keep the history of the odd names to one sentence at most. Ground in scout batch 1
   (Intel SDM / AMD64 manual via felixcloutier or official PDFs), S2 for register list.

2. **What instructions actually do** (~550 words)
   A small working vocabulary, each explained in words: `mov` (including a memory
   operand), `lea` as address arithmetic that touches no memory, `add`/`sub`/`imul`,
   `cmp` setting flags and a conditional jump reading them, `jmp`, `call` and `ret`. The
   AT&T operand order and suffixes recap from chapter 1 in one sentence (S39), then the
   memory operand form `disp(base, index, scale)` with one example. Pose a guiding
   question before showing the answer: "with only compare and jump, how would you write
   `if (n <= 1) return 1;`?" Ground in S39, S40, S41 and scout batch 2.

3. **The stack and stack frames** (~700 words)
   The stack is ordinary memory with `%rsp` pointing at its top, growing toward lower
   addresses. `call` pushes the return address and jumps; `ret` pops it into `%rip`. A
   function's frame: return address, saved `%rbp`, locals at negative offsets from
   `%rbp`. Walk the classic prologue (`push %rbp; mov %rsp, %rbp; sub $N, %rsp`) and
   epilogue (`leave` or `mov %rbp, %rsp; pop %rbp`, then `ret`). Recursion: every call to
   `fact` gets its own frame, which is how each `n` survives. Show the `frames` lab
   output: the `-O0` assembly of `fact`, and the per-call addresses that prove each
   activation's `n` sits at a different, decreasing address. Mention the red zone in one
   or two sentences as a System V detail leaf functions may use. Contrast with the
   reader's interpreter: Go gave his `eval` this for free. Ground in S2 and scout
   batches 2 and 3.

4. **The calling convention: a contract between functions** (~800 words)
   Why a convention exists at all: separately compiled code, from different compilers
   and languages, must agree. The System V AMD64 rules a compiler writer needs:
   integer/pointer arguments in `%rdi, %rsi, %rdx, %rcx, %r8, %r9` and the rest on the
   stack; integer return in `%rax` (and `%rdx` for the upper half of a 128-bit value);
   callee-saved registers `%rbx, %rbp, %r12–%r15` plus `%rsp`, everything else
   caller-saved; the 16-byte stack alignment rule stated precisely (what must hold at the
   `call`, and so what `%rsp` looks like on entry); `%al` holding an upper bound on the
   number of vector registers used for a variadic call such as `printf`. Explain
   caller- vs callee-saved as a division of labor, and ask the reader which kind a
   compiler would rather put a loop counter in when the loop calls a function. Then the
   `abi-contract` lab: a hand-written assembly function called from C that follows the
   rules and works; then the same function breaking one rule (clobbering a callee-saved
   register, or calling with a misaligned stack) and the visible consequence. Close with
   the Go note: Go's internal ABI (ABIInternal, register-based since Go 1.17 on amd64)
   differs from System V, and cgo bridges the two. Ground in S2 and scout batch 3/4.

5. **Reading compiler output** (~500 words)
   How to learn the rest by yourself: `gcc -S` (with `-O0` versus `-O2`, and
   `-fno-asynchronous-unwind-tables` or similar to quiet the `.cfi_` directives, saying
   what those directives are for in one sentence and deferring to chapter 21),
   `objdump -d` showing addresses and the actual bytes (and `-M intel` if he meets Intel
   syntax elsewhere), and Compiler Explorer (godbolt.org) as an interactive version of
   the same. Use the lab's `-O2` `fact` to show what an optimizer does to the frame and
   the recursion, briefly, as a teaser for chapters 14 to 16. Ground in S50, S53 (or a
   current GCC options page from scouts), and scout batch 4.

6. **What `exprc` was doing all along** (~200 words)
   Revisit `compute`: list which rules it obeyed and why it got away with ignoring the
   rest (no arguments, no calls, no locals, no callee-saved registers touched). Map what
   comes next: variables become stack slots (chapter 6 onward), functions become frames,
   and chapter 19 replaces stack slots with registers. No new facts.

## 5. Running example

The recursive C function

```c
long fact(long n) {
    if (n <= 1) return 1;
    return n * fact(n - 1);
}
```

called as `fact(5)` (result 120). It appears in the opening (as the thing `exprc` cannot
yet express), in section 2 (the `if` as compare and jump), in section 3 (its `-O0`
assembly and its stack of frames), in section 4 (argument in `%rdi`, result in `%rax`,
`n` needing to survive the inner call), and in section 5 (its `-O2` form). `compute` from
chapter 1 is the secondary example in the opening and section 6.

## 6. New terms

instruction pointer, general-purpose register, flags register (status flags),
little-endian, memory operand (addressing mode), conditional jump, the stack (machine
stack), stack pointer, return address, stack frame, frame pointer, prologue, epilogue,
red zone, calling convention, ABI (application binary interface), argument registers,
caller-saved register, callee-saved register, stack alignment, disassembler.

Excluded as already in the glossary: register, assembly language, assembler, object file,
linker, compiler driver, stack-machine code generation.

## 7. Misconceptions

1. **"The calling convention is how the CPU works."** The hardware only provides `call`,
   `ret` and a stack pointer; which registers carry arguments and which survive a call is
   a software agreement (the ABI), and different systems use different ones (Windows x64
   differs from System V, and Go's internal ABI differs from both). The chapter should
   leave him saying "System V says", not "x86 does".
2. **"Callee-saved means the callee can't use it."** It means the callee may use it but
   must restore its value before returning, which costs a save and restore. Caller-saved
   registers are free for the callee to destroy, so the caller must save them if it
   needs them after the call.

## 8. Fact questions

Pitfalls file is empty for this topic, so no pitfall questions.

### Batch 1 — The processor's state (suggest S2; search Intel SDM / AMD64 APM, felixcloutier.com)

1. How many general-purpose registers does x86-64 have in 64-bit mode, and what are their
   64-bit names (`%rax` … `%r15`)?
2. What are the 32-, 16- and 8-bit names for the low parts of `%rax` and `%r8` (`%eax`,
   `%ax`, `%al`; `%r8d`, `%r8w`, `%r8b`)?
3. In 64-bit mode, what happens to bits 63:32 of a general-purpose register when an
   instruction writes its 32-bit form, and what happens for 8- and 16-bit writes? (Intel
   SDM vol. 1, 3.4.1.1 or equivalent.)
4. Is x86-64 little-endian, and what does that mean for the byte layout of a 64-bit value
   in memory? (Intel SDM vol. 1.)
5. Which status flags do `cmp` and `sub` set (CF, ZF, SF, OF, …), and which flags does the
   signed condition `jle` test?

### Batch 2 — Instructions and addressing (suggest S39, S40, S41; search felixcloutier.com)

6. What does `call` do on x86-64 (what is pushed, how much `%rsp` changes), and what does
   `ret` do?
7. What does `lea` compute, and does it access memory or change flags?
8. What is the general form of an x86-64 memory operand (base, index, scale 1/2/4/8,
   displacement), and how is it written in AT&T syntax (`disp(base,index,scale)`)?
9. What does `leave` do, exactly, in 64-bit mode?
10. What do the AT&T size suffixes `b`, `w`, `l`, `q` mean (GNU as manual, S39)?

### Batch 3 — The System V AMD64 calling convention (suggest S2; prefer the psABI PDF/source)

11. In order, which registers pass the first six INTEGER-class arguments, and where do the
    remaining arguments go?
12. Which registers return INTEGER-class values (`%rax`, `%rdx`)?
13. Which registers are callee-saved ("preserved across function calls") per the psABI's
    register-usage table, and which are caller-saved?
14. What exactly is the stack alignment requirement: what must be a multiple of 16 (or
    32/64) at function entry, and how does the psABI phrase it?
15. What is the red zone: its size, where it lies relative to `%rsp`, and who may use it?
16. For calls to variadic functions, what does `%al` hold?
17. What does the psABI say about `%rbp` as a frame pointer (is it required or optional)?

### Batch 4 — Other conventions and reading tools (search go.dev source, learn.microsoft.com, gcc.gnu.org, sourceware binutils)

18. What is Go's ABIInternal on amd64: since which Go release do function arguments and
    results pass in registers, which registers does it use for integer arguments, and how
    does it differ from System V? (Go's `src/cmd/compile/abi-internal.md` and the Go 1.17
    release notes.)
19. How does the Windows x64 calling convention differ in its integer argument registers
    (`rcx, rdx, r8, r9`) and its 32-byte shadow space? (Microsoft Learn x64 calling
    convention page.) One sentence's worth only.
20. What does `gcc -S` produce and what do `-O0` and `-O2` mean, per the current GCC
    manual? What do `-fno-asynchronous-unwind-tables` (or `-fno-dwarf2-cfi-asm`) and
    `-fomit-frame-pointer` do, and at which `-O` levels is `-fomit-frame-pointer` enabled?
21. What does `objdump -d` show, and what does `-M intel` change (binutils manual)?
22. What is Compiler Explorer (godbolt.org), and who created it? (Its own site or GitHub
    README.)

## 9. Lab plan

Runner `local` for both. Toolchains from the profile: gcc, as, objdump, gdb, python3, go.
Each lab's `run.sh` should print short, quotable sections with clear headers, and the
lab notes must give line ranges of `run.out` for each section.

1. **`frames`** — the running example at the machine level.
   - Demonstrates: `fact.c` with the running-example `fact` and a `main` that calls
     `fact(5)` and prints the result. Show `gcc -O0 -S` output for `fact` with the
     `.cfi_` noise suppressed (say how), short enough to quote whole. Then make the
     frames visible: either a gdb batch session that breaks in `fact` when `n == 1` and
     prints `bt` plus each frame's `&n` or `$rbp`/`$rsp`, or an instrumented build that
     prints `n` and `&n` per call. The point is five activations, five different
     addresses, decreasing as the stack grows down, each a fixed distance apart. Also
     show `objdump -d` of `fact` (with bytes) from the `-O0` object, and `gcc -O2 -S` of
     `fact` to show the optimizer removing the frame and recursion (whatever gcc actually
     does; report it honestly).
   - Expected result: `success`.
   - Output should make visible: the `-O0` assembly with prologue, the `n` store at a
     negative `%rbp` offset, `cmp`/conditional jump, the recursive `call`, epilogue; the
     per-activation addresses and their spacing; the `objdump` bytes; the `-O2` version.
     Print the gcc version.

2. **`abi-contract`** — the calling convention as a contract you can break.
   - Demonstrates: a hand-written AT&T assembly function (for example `long
     sum3(long a, long b, long c)` or `long add_then_call(long x)` that calls back into a
     C function) called from a C driver, following System V: arguments from `%rdi`,
     `%rsi`, `%rdx`, result in `%rax`, aligned stack at any call it makes, callee-saved
     registers restored. Then one or two deliberate violations, each in its own variant
     and each with a clearly visible effect:
     (a) clobbering a callee-saved register (e.g. `%rbx` or `%r12`) without restoring it,
         where the C caller (driver written so it observably relies on that register,
         for example a hand-checked `-O2` loop, or an asm caller) gets a wrong value;
     (b) calling a C function with a misaligned stack, if a deterministic crash can be
         produced (for example a callee that gcc compiles with an aligned SSE store such
         as `movaps` to a 16-byte-aligned local). If no reliable crash can be produced on
         this machine, say so in the notes and drop (b) rather than faking it.
   - Expected result: `success` for the lab as a whole; the run script runs each variant,
     anticipates the wrong value or the signal, and prints the exit status or signal.
   - Output should make visible: the assembly source of the correct function (short
     enough to quote), its correct result, and for each violation the wrong result or
     signal next to what the correct version printed. If a violation's effect depends on
     how gcc compiled the caller, show the relevant caller instructions so the chapter can
     explain why.
