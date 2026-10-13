# Chapter 2 summary — The machine you compile to

The reader now has a working model of x86-64: memory as addressed bytes, `%rip` driving a fetch-execute loop, sixteen general-purpose registers with their 32/16/8-bit names (32-bit writes zero-extend, 8/16-bit writes do not), little-endian layout, and the ZF/SF/CF/OF status flags. He can read `mov`, memory operands `disp(base,index,scale)`, `lea` as flag-free address arithmetic, `cmp` plus a conditional jump (GCC's inverted `jg` for `if (n <= 1)`), and `call`/`ret`, which push and pop an 8-byte return address and do nothing else.

He traced `fact(5)` at `-O0` with GCC 16: prologue, `n` at `-8(%rbp)`, `leave`/`ret`, and gdb showing five frames 32 bytes apart. He knows the System V rules: arguments in `%rdi, %rsi, %rdx, %rcx, %r8, %r9`, results in `%rax` (and `%rdx`), callee-saved `%rbx, %rbp, %r12–%r15`, 16-byte alignment before `call`, `%al` for variadic calls, and the 128-byte red zone. The `abi-contract` lab showed a silent `%rbx` clobber and a `movaps` SIGSEGV from a misaligned stack. Windows x64 and Go's ABIInternal (nine integer registers, no callee-saved registers, bridged by cgo) differ.

Tools: `gcc -S`, `-O0` vs `-O2` (`fact` became a loop, no frame pointer), `-fno-asynchronous-unwind-tables`, `objdump -dr`, Compiler Explorer.

Open threads: variables as stack slots (ch. 6), instruction selection (18), register allocation and caller/callee-saved choice (19), relocations (20), unwind tables (21).
