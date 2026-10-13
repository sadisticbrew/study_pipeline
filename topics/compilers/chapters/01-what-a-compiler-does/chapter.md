---
topic: Compiler Engineering
chapter: 1
title: What a compiler actually does
---

Your [interpreter]{.term def="A program that takes a program as input and produces the result of executing it."} can already take the text `(7 + 5) * 3 - 6` and print `30`. It reads the characters, turns them into tokens, builds a tree, and walks that tree to compute an answer. Every run repeats all of that work, and the Go program doing the walking has to be installed on the machine for anything to happen at all.

Now run `go build` on that same interpreter. You get one file that runs on a compatible machine with no Go installed anywhere, because the Go runtime is included in the binary [@F46]. Something took Go text and turned it into instructions your processor executes directly [@F45], with no Go-source interpreter at run time. The compiled interpreter still walks the expression tree. That something is a [compiler]{.term def="A program that translates a program written in one language into an equivalent program in another language."}, and the obvious questions are what it produced, in what steps, and whether you could write one for your own little expression language. By the end of this chapter you will have a Go program that turns `(7 + 5) * 3 - 6` into machine instructions which, with a small C driver, run without the expression interpreter and print `30`.

::: crux
When you build a program, what actually happens between the source text and the bytes the processor runs, and how is that different from what your interpreter already does?
:::

## Two ways to run a program

The difference between your evaluator and a compiler is the difference between doing something and writing down how to do it. *Engineering a Compiler* defines a compiler as a program that translates other programs to prepare them for execution [@F1], and an interpreter as something that takes an executable specification as input and produces the result of executing it [@F2]. Your evaluator fits the second definition exactly.

A compiler's output is another program [@F1]. The language it reads is the [source language]{.term def="The language a compiler reads its input program in."} and the language it writes is the [target language]{.term def="The language a compiler writes its output program in."}. For the standard Go compiler used by `go build`, the source language is Go and the target is machine code for the selected processor [@F45].

Picture the tree for our running example. The root is the `-` node. Its left child is a `*` node whose children are a `+` node and the number 3, and its right child is the number 6. The `+` node at the bottom holds 7 and 5. The parentheses are gone, because the tree's shape already says that the addition happens first.

```{.dot caption="The tree for (7 + 5) * 3 - 6. Both the evaluator and the compiler walk this same shape."}
digraph { node [shape=circle]; sub [label="-"]; mul [label="*"]; add [label="+"]; n7 [label="7"]; n5 [label="5"]; n3 [label="3"]; n6 [label="6"]; sub -> mul; sub -> n6; mul -> add; mul -> n3; add -> n7; add -> n5; }
```

Your evaluator walks this tree with a recursive function. At a number it returns the number. At an operator it evaluates both children and combines the results. The compiler we build here walks the very same tree in the very same order, with one change. At each node, instead of computing a value, it writes down the instructions that will compute that value later. Keep that contrast in mind, and the code generator later in this chapter will look almost familiar.

How do you know a translation is right? The program a compiler writes must preserve the behavior required by the source language, so that running the output gives the results the source program would give if you could run it directly. That is the defining property of a correct compiler. Everything clever a real compiler does, such as reordering work, deleting it, or replacing one operation with a cheaper one, is allowed only because it keeps that promise. For C, that promise does not cover undefined behavior such as signed integer overflow [@F57].

::: {.misconception title="Python is interpreted and Go is compiled, that is just what those languages are"}
Words like "compiled" and "interpreted" describe an implementation, not a language. The standard Python implementation translates your source into an internal form before running any of it [@F3], and nothing in Go's definition forbids someone from writing an interpreter for it. The useful habit is to say "this implementation compiles to X, and X is then run by Y".
:::

## A spectrum, not two boxes

Once you see that "compiler" just means "translator", the neat split between compiled and interpreted systems falls apart. Real systems often translate more than once, and they differ in what they translate to and when.

At one end sits [ahead-of-time compilation]{.term def="Translating code before it runs, commonly to machine code."}, or AOT compilation. Go and C usually compile to machine code this way [@F45; @F50]. In that arrangement, the translating happens at build time, and what ships is machine code.

In the middle sits compilation to [bytecode]{.term def="A compact instruction set for a software execution environment, which may interpret it or compile it to machine code."}. CPython compiles Python source into bytecode, which its documentation calls the internal representation of a Python program [@F3], and that bytecode runs on a [virtual machine]{.term def="A software execution environment for an instruction set, which may interpret instructions or compile them to machine code."} which, when interpreting, carries out the machine code corresponding to each bytecode [@F4]. Java makes the same step visible, since the `javac` command compiles Java source into class files that run on the Java Virtual Machine [@F10]. This kind of virtual machine is different from the hypervisor kind. Its interpreter is a loop that reads instructions and acts on them, much like your interpreter.

At the far end sits [just-in-time compilation]{.term def="Compiling parts of a program to machine code while the program is running, usually the parts that run most often."}, or JIT compilation. The HotSpot JVM normally starts applications in a standard interpreter, watches the running code to find the hot spots, and compiles those parts to machine code while leaving seldom-used code uncompiled [@F11]. CPython 3.13 has an experimental version of the same idea. When its bytecode gets hot enough it is translated to an internal form called micro-ops [@F7], which an enabled JIT turns into machine code using copy-and-patch [@F59; @F9], a technique that stitches together prewritten binary fragments and fills in the holes left in them [@F8]. That JIT must be included explicitly at build time, using `--enable-experimental-jit` [@F6] or, on Windows, `PCbuild/build.bat --experimental-jit` [@F58], and is not part of the default build configuration [@F5].

So a Java toolchain using HotSpot combines all three ideas. `javac` translates ahead of time to bytecode [@F10], an interpreter runs that bytecode, and a JIT compiles the hot parts while the program runs [@F11]. Chapter 22 returns to JITs, with your own interpreter as the starting point for one.

## Inside the pipeline

Whatever position a compiler takes on that line, its inside often follows a common design. It is a pipeline of phases that fall into three groups [@F47; @F48; @F49].

The [front end]{.term def="The part of a compiler that reads source text, checks it, and builds an internal representation of the program."} has to understand the source program. It lexes and parses the text into a tree, and then checks that the program makes sense, for example that every variable exists and every operation gets values of the right type [@F13; @F14; @F47]. The [middle end]{.term def="The part of a compiler that improves the program in an internal form, usually largely independent of the source language and target machine."} works on the program in an [intermediate representation]{.term def="A data structure or language a compiler uses to hold the program between reading the source and writing the target."}, or IR, shaped for analysis rather than for people, and tries to make the program better without changing what it does [@F48]. The [back end]{.term def="The part of a compiler that turns the intermediate representation into instructions for one particular target machine."} chooses actual instructions and [registers]{.term key="register" def="A small, very fast storage slot inside the processor that instructions read and write directly."} for one particular processor [@F49].

The Go compiler follows this shape, and the README file in its source tree lists the phases along with the packages that hold their code [@F12]. Parsing, in `cmd/compile/internal/syntax`, holds the lexer, parser and syntax tree [@F13]. Type checking follows in `types2` [@F14]. IR construction, which the authors call "noding", builds the compiler's own tree [@F15]. The middle end does inlining, devirtualization and escape analysis [@F16]. Walk fixes the order of evaluation and removes syntactic sugar [@F17]. Generic SSA converts the IR into static single assignment form, which chapter 12 explains, and runs passes over it [@F18]. Finally, generating machine code does architecture-specific lowering and emits the instructions [@F19]. The first two phases are front end, the last is back end, and the ones in between reshape and improve the program. Chapters 3 to 6 cover the front end, chapter 10 onward covers IRs and the middle end, and chapters 18 to 20 cover the back end.

Why split a compiler this way? Chris Lattner's account of LLVM's design gives the argument in terms of reuse. Without the split, supporting M source languages on N targets would take N times M compilers. With a shared code representation in the middle, a new language needs only a new front end, and the existing optimizer and back ends are reused [@F20]. LLVM's IR exists as an in-memory data structure, as an on-disk bitcode file, and as a human-readable text form [@F21], and the text form is what we look at next.

The `pipeline-peek` lab takes one tiny C function, $f(x) = (x + 5) \cdot 3 - 6$, has `clang` turn it into LLVM IR, and then hands the very same IR file to LLVM's back end, `llc`, twice. Once it targets x86-64 and once it targets AArch64, the 64-bit ARM architecture.

```{.output include="lab/pipeline-peek/run.out" lines="1-18"}
```

Read the IR first. It says to multiply `x` by 3, add 9, and return the result. That is not what the C source said, and it is not a mistake, because $(x + 5) \cdot 3 - 6 = 3x + 15 - 6 = 3x + 9$. This preserves the result for inputs where the C expression does not overflow; signed overflow in C is undefined [@F57]. The middle end already did real work here, folding the constants together before target instructions were chosen. Then each back end picks instructions for its own processor. The x86-64 version does the whole computation in one `leal` instruction, which computes the low 32 bits of `rdi + rdi*2 + 9` into `eax`, then returns. The AArch64 version uses two `add` instructions, the first computing `w0` plus `w0` shifted left by one bit, which is $3x$ in 32-bit arithmetic, and the second adding 9. One IR has become two different machines' code.

There is a catch here, because it is easy to take the wrong lesson from this. IR produced from C is not fully neutral. Clang writes target-specific details into the file, such as a description of the data layout, the target triple, and CPU attributes, so the lab strips those once before both `llc` runs, as the second line of the output reports. That suffices for this function's plain 32-bit integer arithmetic on these two targets, but it is not a general recipe for retargeting C. The M times N argument is about reusing the optimizer and back ends as code, not about any IR file being portable.

A toolchain is also more than a compiler. Compilers commonly write [assembly language]{.term def="A text form of machine instructions that maps almost directly onto the bytes the processor runs."}, which is still text. An [assembler]{.term def="A program that turns assembly language text into machine code."} turns that text into an [object file]{.term def="A file containing machine code and linking information, not yet combined with the other pieces it needs to run."}, and a [linker]{.term def="A program that combines object files and libraries into an executable or library, connecting references between them."} joins object files and libraries into a program you can run [@F50; @F51]. When you type `gcc file.c` or `go build`, you are using a [compiler driver]{.term def="A command that coordinates compilation and linking, and separate assembly when needed, on your behalf."} that coordinates these steps for you and hides them. Go's compiler uses an internal assembler to write an object file rather than passing assembly text to a separate assembler [@F52]. The next section makes the steps visible.

## A compiler you can hold in your head

Time to build one. The `exprc` lab is a Go program of about 140 lines that compiles arithmetic expressions with nonnegative signed 64-bit integer literals, binary `+`, `-`, `*`, `/` and parentheses into x86-64 assembly. Like your interpreter, it has a lexer, a parser and a tree walker, and the first two are what you have already written. The parser uses precedence climbing so that `*` binds tighter than `-` and operators group left to right. Chapters 3 to 5 treat both properly, so here all that matters is that they produce the tree from the first section.

The interesting part is the walker. Before reading it, think about what it has to produce. The processor has no idea what a tree is. It runs instructions, working on registers and memory. So every node in this expression language can turn into a straight-line list of instructions, and the result of a subtree has to sit somewhere the instructions for its parent can find.

The trick `exprc` uses is called [stack-machine code generation]{.term def="Generating code that keeps every intermediate result on a stack, pushing operands and popping them when an operation needs them."}. Every subtree leaves exactly one value on the machine's stack, and nothing else. `pushq` moves the stack pointer `%rsp` down by 8 bytes and stores its operand at the new top of the stack [@F29]. `popq` does the reverse, copying the top value into a register and moving `%rsp` back up by 8 [@F30]. Chapter 2 explains the stack properly. For now, think of it as a pile of 8-byte values where you can only touch the top.

So what should the code for a single number be? It must leave that number on the stack, and nothing else, which means loading it into a register and pushing it. And what about `a + b`? If the code for `a` leaves one value on the stack and the code for `b` leaves one more on top, then running both leaves the two operands stacked up, with `b` on top. Pop them both, add them, and push the sum. The subtree as a whole has left exactly one value, so the rule holds at every level. Here is the whole generator:

```{.go include="lab/exprc/main.go" lines="103-122"}
```

Put this next to your evaluator. Where your evaluator returns `n.value`, this function prints an instruction that will push `n.value`. Where your evaluator returns `eval(left) + eval(right)`, this one prints the code for the left child, then the code for the right child, then the instructions that combine them. Your evaluator does the arithmetic now, and this one writes it down for later.

The instructions are written in AT&T syntax, which the GNU assembler uses by default [@F36]. The source operand comes first and the destination second for the two-operand arithmetic instructions here, the opposite of Intel's manuals, a convention kept for compatibility with older Unix assemblers [@F35]. Registers start with `%` and constants with `$` [@F53]. So `movabsq $7, %rax` puts the 64-bit number 7 into register `%rax` [@F54]. `popq %rcx; popq %rax` takes the right operand off the stack into `%rcx` and then the left operand into `%rax`. `addq %rcx, %rax` adds `%rcx` into `%rax`, `subq` subtracts it, and `imulq` multiplies. The semicolons are a convenience of this lab. The assembler treats each one like a line break [@F55], so each line of the listing packs two or three ordinary instructions.

The pieces are put together in `main`:

```{.go include="lab/exprc/main.go" lines="134-141"}
```

Lexer, parser, generator, in that order, which is the front end and back end of the previous section with no middle end at all. Around the generated instructions, `main` writes a few lines that turn them into a function named `compute`. At the end, `popq %rax` takes the single value the whole tree left on the stack and puts it in `%rax`, and `ret` returns. The value goes in `%rax` because the System V calling convention for x86-64 Linux says a 64-bit integer return value comes back in that register [@F27], so any C code calling `compute` with the driver's declaration will look for it there.

Something has to call `compute`. Following Abdulaziz Ghuloum's approach of starting a compiler with a small C runtime that calls the compiled entry point and prints what it returns [@F25], the lab has a ten-line C driver:

```{.c include="lab/exprc/driver.c"}
```

Now run the compiler on the running example. Before looking, predict how many `pushq` instructions it will contain, given that the tree has four numbers and three operators.

```{.output include="lab/exprc/run.out" lines="1-19"}
```

The first two lines show that `exprc` succeeded and that the only file it wrote is `example.s`, which is still just a text file. The listing follows the tree exactly. Push 7, push 5, pop both and add, push 12. Push 3, pop both and multiply, push 36. Push 6, pop both and subtract, push 30. Then the final pop puts 30 into `%rax`. Each of the four numbers and three operators produced one push, so seven in all. The last line is a marker telling the linker that this code does not need an executable stack [@F56].

Turning that text into a program is the job of the rest of the toolchain:

```{.output include="lab/exprc/run.out" lines="20-23"}
```

The first `gcc` command, with `-c`, runs only the assembler and turns `example.s` into the object file `example.o` [@F51]. The second compiles and assembles `driver.c`, then runs the linker to join both object files and the C library into the executable `example` [@F50]. The file list shows which program made what. Your compiler made the `.s`, and `gcc` as a driver made everything after it. The executable prints `30`, and you have written a compiler.

::: {.misconception title="The compiler produces the executable"}
A native compiler commonly produces assembly or an object file, not the final executable [@F50; @F52]. In this lab you can see the boundary, because `exprc` wrote only `example.s` and the object file and executable appeared only after `gcc` ran the assembler and linker. Drivers such as `gcc` and `go build` coordinate the necessary steps in one command, which is why the boundary is usually invisible.
:::

One honest edge remains. What should `10 / (5 - 5)` do? Your evaluator would hit the division at evaluation time and could report an error. This compiler never evaluates subtrees, so it happily produces code.

```{.output include="lab/exprc/run.out" lines="24-26"}
```

The compiler exited with status 0, and the program it produced printed nothing and was killed by a signal. Division is the one case the generator handles differently. The 64-bit signed divide `idivq` divides the 128-bit value held across `%rdx` and `%rax` by its operand, leaving the quotient in `%rax` and the remainder in `%rdx` [@F31]. That is why `cqto` comes first, since it fills every bit of `%rdx` with the sign bit of `%rax` [@F32], turning the 64-bit dividend into a 128-bit one. When the divisor is 0, or the signed quotient is too large for its destination, `idiv` raises a divide-error exception [@F33], and Linux on x86 responds by sending the process `SIGFPE` [@F34]. Errors your interpreter would find while evaluating can become, in a compiled program, events that happen long after the compiler has finished. A compiler can catch some of them early when it can prove something about the values involved, but this one never looks.

::: tryit
Trace `exprc` by hand on `8 - 2 - 1` before reading any code. First decide what tree the parser builds, given that operators group left to right. Then write the instruction lines the generator prints for that tree, and follow the stack after each line. Check that you end with 5 in `%rax`. Then do the same for `8 - (2 - 1)`, which should give 7, and compare the two listings. If you have the lab on disk, run `exprc` on both and compare them with your traces.
:::

## The compiler that compiles itself

The Go compiler is written in Go, which should bother you a little. To build it you need a Go compiler, which must itself have been built. The way out is [bootstrapping]{.term def="Building a compiler using an earlier compiler, so that a language's compiler can eventually be built from itself."}. One route is to build the first version using a compiler for another language, and from then on build later releases using an earlier release. If the compiler is written in the language it compiles, the language has a [self-hosting compiler]{.term def="A compiler written in the same language it compiles."}.

Go took this step in version 1.5. From that release on, the compiler and runtime have been written entirely in Go with a little assembler, and the C compiler that was once needed to build the distribution is gone [@F37]. The conversion was done by automatic translation of the C code into Go, and the authors stress that the result was the same program in a different language, not a new implementation, so they did not expect new compiler bugs from the move [@F38]. Building Go from source today still needs an older Go. Releases from 1.5 to 1.19 needed Go 1.4, 1.20 and 1.21 needed Go 1.17, and 1.22 and 1.23 needed Go 1.20 [@F40]. The current policy is that Go 1.N needs Go 1.M, where M is N minus 2, rounded down to an even number, so Go 1.24 and 1.25 need Go 1.22 [@F39]. You can apply the rule yourself to whatever version you have installed.

Rust does the same thing in visible stages. Stage 0 is a prebuilt compiler and standard library, stage 1 is built from the current source by that earlier compiler, and stage 2 is the truly current compiler [@F41], produced by rebuilding the compiler with stage 1 [@F42]. Stage 1 has the new compiler's logic but was compiled by old code, while stage 2 is the new compiler built by itself.

Bootstrapping has an uncomfortable consequence, and Ken Thompson showed it in his 1984 Turing Award lecture, "Reflections on Trusting Trust". He described a compiler binary modified so that, even after the malicious code is removed from the compiler's source, the binary puts it back every time it compiles itself, while also planting a backdoor in the `login` command, with no trace in any source file [@F43]. His moral was that you cannot trust code you did not totally create yourself, and that no amount of source-level verification protects you from untrusted code [@F44]. A compiler built by an earlier binary inherits this trust problem, and reading its source alone does not tell you what that binary did.

## What you now have, and what is missing

You have a real compiler. It reads a language, builds a tree, and writes x86-64 assembly that a standard toolchain turns into a working program. It also skips almost everything that makes real compilers hard. It has no variables, so there is no name resolution, which chapter 6 adds, and only one implicit type, signed 64-bit integers, rather than the type systems chapters 7 to 9 cover. It has no separate IR beyond the tree, so the tree goes straight to instructions, and chapters 10 to 13 put a lower-level IR in between [@F47]. It does no optimization, so `(7 + 5) * 3 - 6` is computed at run time even though the answer is known at compile time, and chapters 14 to 17 fix that. It uses the stack for every intermediate value instead of keeping values in registers, which chapters 18 and 19 address. And it leans on the machine knowledge chapter 2 is about to give you properly.

## Check yourself

::: selftest
1. Your evaluator and `exprc` both walk the tree for `(7 + 5) * 3 - 6`. Name the one thing each does at a `+` node, and explain how this generator's walk order preserves which operand is left and which is right.
2. A friend says Java is interpreted. Using HotSpot as the example, describe all the translation steps a Java method may go through, and say which ones happen before the program starts and which during.
3. In the `pipeline-peek` output, the IR already says `mul` by 3 and `add` 9. Which part of the pipeline produced that, and what would you expect the IR to look like if that part did nothing?
4. Predict the output of `exprc` for the single expression `42`. How many lines of instructions appear between `compute:` and `ret`, and what does each do?
5. `exprc` compiles `9 / 0` without complaint. Why can it not report this as an error in its current design, and what would it need to do to catch it?
6. Suppose you rewrote `exprc` to emit LLVM IR text instead of x86-64 assembly. Which two pieces of the lab would you no longer need to write yourself, and what new thing would you gain?
:::

::: answers
1. At a `+` node the evaluator computes the left value, the right value and their sum, and returns it. `exprc` emits the code for the left child, then the code for the right child, then `popq %rcx; popq %rax` followed by `addq` and `pushq`. This order puts the right operand on top, so the pops recover the right operand into `%rcx` and the left into `%rax`. For `-` and `/`, swapping the operands changes the answer. A different walk order could still be correct if the generator changed how it retrieved the operands.
2. `javac` translates source to class files of bytecode before the program runs. When the program starts, HotSpot interprets that bytecode. While it runs, HotSpot finds the hot methods and compiles them to machine code, so that part happens during execution. The language never decided any of this. The implementation did.
3. The middle end, running clang's optimizations at `-O1`, folded $(x + 5) \cdot 3 - 6$ into $3x + 9$. Without that work the IR would follow the source literally, with an add of 5, a multiply by 3 and a subtract of 6.
4. Two lines of instructions. `movabsq $42, %rax; pushq %rax` pushes 42, which is the rule for a number node, and then `popq %rax` takes it back off before `ret`. The push followed by a pop is wasted work, which is exactly the kind of thing an optimizer removes.
5. The code generator only emits instructions and never computes values, so it never sees that the divisor is 0. It could catch this case by evaluating constant subtrees while compiling, which is constant folding. That works here because every value is a constant. Once programs read input, constant folding still works on constant subtrees, but cannot determine every runtime value.
6. You would no longer write the x86-64 instruction choices or worry about allocating the target's registers, because `llc` would be your back end [@F49]. You would gain access to other targets supported by your LLVM installation, subject to their runtime and calling-convention requirements, and could run LLVM's optimizer before `llc` [@F60], which is Lattner's M times N argument from your own side as a front end author [@F20].
:::
