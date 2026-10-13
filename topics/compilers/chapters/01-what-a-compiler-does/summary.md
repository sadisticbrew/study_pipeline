# Chapter 1 summary — What a compiler actually does

The reader now separates an interpreter, which produces the result of running a program, from a compiler, which translates a program from a source language into an equivalent program in a target language. A correct compiler preserves the behavior the source language requires, and C's undefined behavior, such as signed overflow, is outside that promise. "Compiled" and "interpreted" describe implementations, not languages. Ahead-of-time compilation, bytecode run by a virtual machine (CPython, `javac` plus the JVM), and just-in-time compilation (HotSpot, CPython 3.13's experimental copy-and-patch JIT, off by default) lie on one spectrum, and real toolchains combine them.

He knows the common front end, middle end and back end split, with an intermediate representation in the middle. He has seen it in the Go compiler README's phases (parsing, `types2`, noding, middle end, walk, generic SSA, machine code), and in Lattner's M times N reuse argument. The `pipeline-peek` lab showed clang's `-O1` folding `(x + 5) * 3 - 6` into `3x + 9` and one IR file lowered to x86-64 and AArch64. It also showed that clang IR is not target-neutral. Assembler, object file, linker and compiler driver are distinct steps.

He built `exprc`, a Go compiler using stack-machine code generation (push, pop, `%rax` return, `cqto`/`idivq`, AT&T syntax). Its division by zero dies at run time with SIGFPE. He also learned bootstrapping (Go 1.5's automatic C-to-Go translation, Go's version policy, rustc's stages) and Thompson's trusting-trust attack.

Open threads: the machine and stack (ch. 2), real front ends (3 to 6), types (7 to 9), lower-level IR (10 to 13), optimization including constant folding (14 to 17), registers (18 to 20), JITs (22).
