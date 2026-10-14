---
topic: Compilers
chapter: 2
title: The machine you compile to
---

In chapter 1, `exprc` compiled `(7 + 5) * 3 - 6`, a small C driver called the generated `compute` function, and the program printed `30`. Now suppose you want your language to have functions, starting with the classic one, a factorial that calls itself on `n - 1`. The moment you try to generate code for it, three questions appear that the stack-machine trick never had to answer. Where does `n` live while the inner call runs, given that the inner call has an `n` of its own? How does the inner call know where to come back to when it finishes? And if your generated code calls a C function such as `printf`, which registers still hold your values afterward, and what does `printf` expect to find on the stack?

The processor answers only the [return address]{.term def="The address of the instruction just after a call, saved on the stack so the callee's ret can resume the caller there."} question by itself [@F9; @F10]. The rest are answered by a written agreement, a [calling convention]{.term def="The set of rules that says how functions pass arguments, return results, and share registers and the stack."}, that interoperating compilers follow. Ask yourself: why did `compute` work when called from C, and what would it need to change if it took an argument or called `printf`? By the end you will be able to read GCC's output for a recursive factorial, point at each of its frames, and write an assembly function that C can call safely.

::: crux
What does the machine a compiler targets actually provide, in registers, memory, a stack and a handful of instruction kinds, and what rules must generated code follow so that functions, including recursive ones and ones built by other compilers, can call each other correctly?
:::

## What the processor gives you

Start with the plain model, because everything else hangs on it. Memory is a huge array of bytes, and each byte has a number, its address. The processor sits next to that array with a small set of registers of its own. One special register, the [instruction pointer]{.term def="The register that holds the address of the next instruction the processor will execute, called %rip on x86-64."}, says where the next instruction is [@F54]. The processor's whole life is a loop. It fetches the instruction at `%rip`, does what it says, moves `%rip` forward to the next one, and repeats. A jump is nothing more than an instruction that writes a new value into `%rip`.

On x86-64, the registers your code works with day to day are the [general-purpose registers]{.term key="general-purpose register" def="A register that ordinary instructions can use for any integer or address value."}. In 64-bit mode there are sixteen of them [@F1], named `%rax`, `%rbx`, `%rcx`, `%rdx`, `%rsi`, `%rdi`, `%rsp`, `%rbp` and `%r8` through `%r15` [@F2]. The first eight carry their names from older 16-bit and 32-bit versions of the architecture [@F55], and the last eight were simply numbered when 64-bit mode added them [@F56].

Each register also has names for its lower parts. The low 32 bits of `%rax` are `%eax`, the low 16 bits are `%ax`, and the low byte is `%al`. The numbered registers use suffixes instead, so `%r8d`, `%r8w` and `%r8b` are the 32-, 16- and 8-bit parts of `%r8` [@F3].

Writing through these narrower names follows a rule compilers lean on constantly. When an instruction writes a 32-bit name such as `%eax`, the processor also sets the upper 32 bits of `%rax` to zero, so the whole register holds the 32-bit result with zeros above it [@F4]. Widening a value by filling the new high bits with zeros is called [zero extension]{.term def="Widening a value to more bits by filling the new high bits with zeros."}. Writing an 8-bit or 16-bit name works differently, because it changes only those low bits and leaves the rest of the register as it was [@F5]. So `movl $1, %eax` sets all of `%rax` to 1, and it is shorter to encode than the 64-bit form [@F60], a trick you will see GCC use in a moment.

When a 64-bit value goes to memory, its eight bytes have to be laid out in some order. x86-64 is [little-endian]{.term def="Storing a multi-byte value with its least significant byte at the lowest address."}, which means the bytes of a value are numbered starting from the least significant one [@F6]. The value 1 stored at address 1000 puts `01` at address 1000 and seven zero bytes after it.

The last piece of state in this plain model is the [flags register]{.term def="A register whose status bits record facts about arithmetic or compare results, such as whether they were zero or negative."}. Arithmetic and compare instructions set its status bits as a side effect, though not every instruction sets every flag. The four that matter most are the Zero Flag (ZF), set when the result was zero, the Sign Flag (SF), a copy of the result's sign bit [@F48], the Carry Flag (CF), the carry or borrow out of an unsigned operation [@F49], and the Overflow Flag (OF), set on signed overflow [@F50]. Later instructions can read these bits and decide what to do.

## What instructions actually do

A compiler's back end needs surprisingly few kinds of instruction to express everything C can say. You met [AT&T syntax]{.term def="The assembly syntax GNU tools use by default, with the source operand first and size suffixes on many mnemonics."} in chapter 1. The source comes first and the destination last, and a size suffix on the mnemonic gives the size, with `b`, `w`, `l` and `q` meaning 8, 16, 32 and 64 bits [@F17].

The workhorse is `mov`, which copies a value. Its operands can be a constant such as `$1`, a register, or a [memory operand]{.term def="An instruction operand that names a location in memory by computing its address from registers and a constant."}. The usual form of a memory operand is a base register plus an index register times a scale of 1, 2, 4 or 8, plus a constant displacement, and AT&T syntax writes it as `disp(base, index, scale)` [@F13; @F57]. Most of the time you see the short versions. `-8(%rbp)` means an address 8 below the address in `%rbp`; the instruction's operand size determines how many bytes it accesses. `(%rdi,%rcx,8)` reaches element `i` of an array of 8-byte values when `%rdi` holds the array's start and `%rcx` holds `i`.

The instruction `lea` takes a memory operand but never touches memory. It computes the address the operand describes and puts that number in the destination register [@F11], and it changes no flags [@F12]. Compilers use it as a cheap calculator. `leaq 1(%rdi,%rdi,2), %rax` puts `3 * %rdi + 1` into `%rax` in one instruction.

You know `add`, `sub` and `imul` from `exprc`. The new arrival is `cmp`, which subtracts one operand from the other, throws the difference away and keeps only the flags, setting the same ones `sub` would [@F47]. After it, a [conditional jump]{.term def="A jump that changes %rip only if its condition holds, usually a test of flag bits, and otherwise falls through to the next instruction."} reads those flags. `jle`, for example, jumps when ZF is set or when SF and OF differ [@F8], which is precisely "the destination value was less than or equal to the source value" for signed numbers after an AT&T-syntax `cmp`. `jmp` jumps always.

Now a guiding question. With only compare and jump, how would you write `if (n <= 1) return 1;`? There are no blocks and no `if` statement, only labels. Try it before reading on.

One answer is to compare `n` with 1, jump to the "return 1" code if less or equal, and otherwise fall through to the recursive case. The answer GCC prefers flips the test. It compares `n` with 1 and jumps *past* the "return 1" code when `n` is greater, so the short case sits right after the compare. Both work. You will see the flipped form, `jg`, in GCC's output below, and once you know to expect the inverted condition, compiler output becomes much easier to read.

That leaves `call` and `ret`, the two instructions that make functions possible at the hardware level. `call` pushes the address of the instruction after itself onto the stack and then jumps to the target [@F9]. `ret` pops that saved address off the stack into the instruction pointer and carries on from there [@F10]. These ordinary near-call and return instructions do not pass arguments, save general-purpose registers, or reserve space for locals. Everything beyond remembering where to come back to is left to software.

Follow one call through two pieces of state. Before it, `%rip` points at `call fact`. The `call` pushes the address of the next instruction and jumps, so on entry to `fact` that address is the top of the stack [@F9; @F23]. When `fact` finishes, `ret` pops it into `%rip` and the caller carries on [@F10].

```{.dot caption="One call and its return, as seen in the instruction pointer and the top of the stack."}
digraph { node [shape=plaintext]; ranksep=0.3;
  a [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
    <TR><TD COLSPAN="2" BORDER="0">before the call</TD></TR>
    <TR><TD>%rip</TD><TD>call fact</TD></TR>
    <TR><TD>top of stack</TD><TD>caller's data</TD></TR></TABLE>>];
  b [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
    <TR><TD COLSPAN="2" BORDER="0">on entry to fact</TD></TR>
    <TR><TD>%rip</TD><TD>first instruction of fact</TD></TR>
    <TR><TD>top of stack</TD><TD>return address</TD></TR></TABLE>>];
  c [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
    <TR><TD COLSPAN="2" BORDER="0">after the return</TD></TR>
    <TR><TD>%rip</TD><TD>instruction after the call</TD></TR>
    <TR><TD>top of stack</TD><TD>caller's data</TD></TR></TABLE>>];
  a -> b [label="  call pushes the address of the next instruction, then jumps"];
  b -> c [label="  fact runs, then ret pops that address into %rip"];
}
```

Nothing else connects a call to its return. `ret` takes whatever is on top of the stack, so `fact` must leave `%rsp` pointing at the return address by the time it returns.

## The stack, and a frame for every call

The [machine stack]{.term def="A region of ordinary memory that functions use for return addresses, saved registers and local variables, growing and shrinking as calls happen."} is not special hardware. It is ordinary memory, and the only thing that makes it a stack is the [stack pointer]{.term def="The register %rsp, which holds the address of the current top of the machine stack."}, `%rsp`, which points at its top. The stack grows toward lower addresses [@F61]. As you learned with `exprc`, `pushq` moves `%rsp` down by 8 and stores, and `popq` loads and moves it back up. Since `call` pushes, the value it pushes, the return address, is an 8-byte slot sitting right at the top of the stack when a function starts in 64-bit mode [@F45; @F46].

The interesting part is the stack below that return address, and `fact` shows why a function needs it. Its `n` arrives in a register and has to survive the recursive call, but the recursive call will put its own `n` in that same register. In this unoptimized code, the value goes to memory, somewhere the inner call will not reuse. So each call claims a fresh block of stack below whatever its caller was using, called the function's [stack frame]{.term def="The block of stack memory one function call owns, holding its saved registers and local variables."}, and each activation gets its own copy of `n`. Your Go interpreter's recursive `eval` got this for free, because the Go compiler built a frame for every call to `eval`. Here you see what that costs.

### Prologue and epilogue

Here is what GCC produces for `fact` with optimization turned off.

```{.output include="lab/frames/run.out" lines="4-21"}
```

The first three instructions are the [prologue]{.term def="The instructions at the start of a function that set up its stack frame."}. `pushq %rbp` saves the caller's `%rbp`. `movq %rsp, %rbp` makes `%rbp` point at the new frame, and from now on `%rbp` is the [frame pointer]{.term def="A register, usually %rbp, that holds a fixed address inside the current frame so locals can be found at constant offsets from it."}, a fixed anchor for this call while `%rsp` is free to move. `subq $16, %rsp` claims 16 bytes for locals. Then `n` is copied from `%rdi` into its slot at `-8(%rbp)`.

The body is the compare and jump from the last section. `cmpq $1, -8(%rbp)` compares `n` with 1, and `jg .L2` jumps to the recursive case if `n` is greater. Otherwise the code falls into `movl $1, %eax`, the 32-bit write that clears the upper half of `%rax`, and jumps to the end. In the recursive case, `n - 1` is computed and placed in `%rdi`, `call fact` runs the inner activation, and when it returns, `imulq -8(%rbp), %rax` multiplies its result by this activation's own `n`, read back safely from memory.

The last two instructions are the [epilogue]{.term def="The instructions at the end of a function that tear down its stack frame and return."}. `leave` copies the frame pointer into the stack pointer, which releases the frame, and then pops the saved `%rbp` back [@F15]. In 64-bit mode it works on the full 64-bit registers by default [@F16]. `ret` then returns to the caller.

On entry, `%rsp` points at the return address and `%rbp` still holds the caller's value. The first two instructions save that value below the return address and point `%rbp` at the saved copy. `subq` then moves `%rsp` down 16 bytes, and `n` goes in the upper of the two new slots, leaving the lower one unused.

```{.dot caption="The prologue of fact read downward and its epilogue read upward, with higher addresses at the top."}
digraph { node [shape=plaintext]; ranksep=0.35;
  s1 [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
    <TR><TD COLSPAN="3" BORDER="0">on entry, %rbp still the caller's</TD></TR>
    <TR><TD BORDER="0" WIDTH="58"></TD><TD WIDTH="110">caller's frame</TD><TD BORDER="0" WIDTH="80"></TD></TR>
    <TR><TD BORDER="0"></TD><TD>return address</TD><TD BORDER="0" ALIGN="LEFT">← %rsp</TD></TR></TABLE>>];
  s2 [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
    <TR><TD COLSPAN="3" BORDER="0">after the first two instructions</TD></TR>
    <TR><TD BORDER="0" WIDTH="58"></TD><TD WIDTH="110">caller's frame</TD><TD BORDER="0" WIDTH="80"></TD></TR>
    <TR><TD BORDER="0"></TD><TD>return address</TD><TD BORDER="0"></TD></TR>
    <TR><TD BORDER="0"></TD><TD>saved %rbp</TD><TD BORDER="0" ALIGN="LEFT">← %rsp, %rbp</TD></TR></TABLE>>];
  s3 [label=<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">
    <TR><TD COLSPAN="3" BORDER="0">after subq and the store of n</TD></TR>
    <TR><TD BORDER="0" WIDTH="58"></TD><TD WIDTH="110">caller's frame</TD><TD BORDER="0" WIDTH="80"></TD></TR>
    <TR><TD BORDER="0" ALIGN="RIGHT">8(%rbp)</TD><TD>return address</TD><TD BORDER="0"></TD></TR>
    <TR><TD BORDER="0" ALIGN="RIGHT">0(%rbp)</TD><TD>saved %rbp</TD><TD BORDER="0" ALIGN="LEFT">← %rbp</TD></TR>
    <TR><TD BORDER="0" ALIGN="RIGHT">-8(%rbp)</TD><TD>n</TD><TD BORDER="0"></TD></TR>
    <TR><TD BORDER="0" ALIGN="RIGHT">-16(%rbp)</TD><TD>unused</TD><TD BORDER="0" ALIGN="LEFT">← %rsp</TD></TR></TABLE>>];
  s1:sw -> s2:nw [label="pushq %rbp\lmovq %rsp, %rbp\l"];
  s2:sw -> s3:nw [label="subq $16, %rsp\lmovq %rdi, -8(%rbp)\l"];
  s3:ne -> s2:se [label="leave, part 1:\lcopy %rbp to %rsp\l"];
  s2:ne -> s1:se [label="leave, part 2:\lpop %rbp\l"];
}
```

Read upward, the same snapshots are the epilogue. The first half of `leave` discards the locals by moving `%rsp` up to `%rbp`, and the second half pops the caller's `%rbp`, leaving `%rsp` on the return address for `ret`. The offsets on the left are the standard System V layout, with the return address at `8(%rbp)` and the caller's `%rbp` at `0(%rbp)` [@F62]. Every slot keeps a fixed offset from `%rbp`, however `%rsp` moves.

### Watching five frames

The frames lab runs `fact(5)` under gdb with a breakpoint on `fact`, and at each entry it prints how far this activation's `&n` sits from the first one.

```{.output include="lab/frames/run.out" lines="53-58"}
```

Five activations, five different addresses, each 32 bytes below the last. Count what each call adds and the spacing explains itself. `subq $16` reserves 16 bytes and the saved `%rbp` takes 8, and the remaining 8 bytes of the 32 are the return address that `call` pushed [@F46]. Since `fact` makes no other pushes, every frame is the same size, so the addresses step down evenly. Here are the first three of those frames while `fact(3)` runs.

```{.dot caption="The stack while fact(3) runs, with one 32-byte frame per activation and higher addresses at the top."}
digraph { node [shape=plaintext];
  t [label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="2">
    <TR><TD></TD><TD><TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="3">
      <TR><TD WIDTH="160">main's frame</TD><TD BORDER="0" WIDTH="50"></TD></TR></TABLE></TD></TR>
    <TR><TD ALIGN="RIGHT">fact(5),<BR/>32 bytes</TD><TD><TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="3">
      <TR><TD WIDTH="160">return address into main</TD><TD BORDER="0" WIDTH="50"></TD></TR>
      <TR><TD>saved %rbp: main's</TD><TD BORDER="0"></TD></TR>
      <TR><TD>n = 5</TD><TD BORDER="0"></TD></TR>
      <TR><TD>unused</TD><TD BORDER="0"></TD></TR></TABLE></TD></TR>
    <TR><TD ALIGN="RIGHT">fact(4),<BR/>32 bytes</TD><TD><TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="3">
      <TR><TD WIDTH="160">return address: imulq in fact</TD><TD BORDER="0" WIDTH="50"></TD></TR>
      <TR><TD>saved %rbp: fact(5)'s</TD><TD BORDER="0"></TD></TR>
      <TR><TD>n = 4</TD><TD BORDER="0"></TD></TR>
      <TR><TD>unused</TD><TD BORDER="0"></TD></TR></TABLE></TD></TR>
    <TR><TD ALIGN="RIGHT">fact(3),<BR/>32 bytes</TD><TD><TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="3">
      <TR><TD WIDTH="160">return address: imulq in fact</TD><TD BORDER="0" WIDTH="50"></TD></TR>
      <TR><TD>saved %rbp: fact(4)'s</TD><TD BORDER="0" ALIGN="LEFT">← %rbp</TD></TR>
      <TR><TD>n = 3</TD><TD BORDER="0"></TD></TR>
      <TR><TD>unused</TD><TD BORDER="0" ALIGN="LEFT">← %rsp</TD></TR></TABLE></TD></TR>
  </TABLE>>];
}
```

Look at the return addresses. The ones in the `fact(4)` and `fact(3)` frames are the same address, the `imulq` right after `call fact`, because both were pushed by that one instruction [@F9]. What keeps the activations apart is the chain of saved `%rbp` values. When `fact(3)` returns, its `leave` restores `fact(4)`'s frame pointer [@F15], so the `imulq` that runs next reads `fact(4)`'s `n` from `-8(%rbp)`.

::: {.aside title="The red zone"}
System V reserves the 128 bytes just below `%rsp` and forbids signal and interrupt handlers from modifying them [@F24]. A function may keep temporary data there that is not needed across calls, and a leaf function, one that calls nothing, may use it as its entire frame without moving `%rsp` at all [@F25]. This is called the [red zone]{.term def="The 128 bytes below %rsp that System V guarantees no signal handler will overwrite, usable by a function as scratch space."}. `fact` calls itself, so it cannot use it for `n`.
:::

## The calling convention: a contract between functions

The frame layout above is something one function decides for itself. The moment two functions talk, they need shared rules. `fact`'s caller put the argument in `%rdi` and expected the answer in `%rax`. Nothing in the hardware says it must be those registers. It works because both sides were compiled against the same agreement, and that agreement has to cover code built by different compilers, at different times, in different languages. The agreement is part of the [ABI]{.term def="Application binary interface, the rules compiled code must follow to interoperate, including the calling convention and data layout."}, and for interoperating with C on Linux for x86-64 the one that matters is the System V ABI.

::: {.misconception title="The calling convention is just how the CPU works"}
The hardware provides `call`, `ret` and a stack pointer, but not the argument-passing and register-preservation rules. Which registers carry arguments and which survive a call is a software agreement, and other systems chose differently. Windows x64 passes integer arguments in the first four argument positions in `%rcx`, `%rdx`, `%r8` and `%r9` [@F58], and the caller always reserves stack space for four register parameters even if the callee takes fewer [@F34], which at 8 bytes each is the 32 bytes Windows programmers call shadow space. Say "System V says", not "x86 does".
:::

### The rules a compiler writer needs

For arguments that are all integers or pointers of at most 64 bits, the first six go in the [argument registers]{.term key="argument register" def="The registers a calling convention assigns to pass a function's first arguments."}, `%rdi`, `%rsi`, `%rdx`, `%rcx`, `%r8` and `%r9`, in that order [@F18]. Arguments that do not fit go on the stack [@F19]. An integer result comes back in `%rax`, and a second eight bytes, such as the upper half of a 128-bit value, comes back in `%rdx` [@F20].

General-purpose registers are split into two kinds, apart from `%rsp`. `%rbx`, `%rbp` and `%r12` through `%r15` belong to the caller, and a called function must preserve their values [@F21]. These are [callee-saved registers]{.term key="callee-saved register" def="A register a called function may use only if it restores the original value before returning."}. The other general-purpose registers belong to the called function [@F21], so they are [caller-saved registers]{.term key="caller-saved register" def="A register a called function may overwrite freely, so a caller that needs its value after the call must save it first."}. `%rsp` is in a class of its own, since the callee must leave it exactly where it found it for `ret` to work.

::: {.misconception title="Callee-saved means the callee cannot use it"}
The callee may use a callee-saved register as much as it likes. It just has to put the original value back before returning, which can cost a push and a pop. Caller-saved registers are the reverse. The callee may destroy them for free, so if the caller still needs a value in one after the call, the caller must save it.
:::

This is a division of labor, and each side pays only when it needs to. Here is a question for you. A loop runs a million times and calls a function on every iteration. Which kind of register would a compiler rather keep the loop counter in? A caller-saved register would have to be saved and restored around every one of the million calls. A callee-saved register costs one save and one restore in the prologue and epilogue of the function that owns the loop, and the callee guarantees it survives each call. Chapter 19, on register allocation, is where this choice gets made systematically.

The stack must be aligned too. The psABI requires at least 16-byte alignment immediately before `call`, so that on function entry, with the return address just pushed, `%rsp + 8` is a multiple of 16 [@F23]. Passing `__m256` or `__m512` arguments on the stack raises this to 32 or 64 bytes [@F22]. This is precisely what [stack alignment]{.term def="The rule that %rsp must be a multiple of some size, 16 bytes here, at a particular point in a call."} means. So inside a function, `%rsp` starts 8 bytes off a 16-byte boundary, which must be fixed before any call. `fact`'s prologue `pushq %rbp` does that, and `subq $16` keeps it fixed.

One last rule matters as soon as you call `printf`. For calls to variadic functions, `%al` is a hidden argument giving an upper bound, from 0 to 8, on the number of vector registers used [@F26; @F27]. If you pass no arguments in vector registers, setting `%al` to 0 is enough.

### Breaking the contract

The abi-contract lab has a hand-written `sum3` that adds its three arguments and passes the total through a C function `echo` before returning it.

```{.s include="lab/abi-contract/correct.s" lines="4-12"}
```

It keeps the sum in `%rbx`, which is callee-saved, so it saves the caller's `%rbx` first. That one `pushq` does double duty. It also moves `%rsp` from 8 off a 16-byte boundary to on one, so the `call echo` happens with an aligned stack. The broken variant replaces `pushq %rbx` with `subq $8, %rsp` and the matching pop with `addq $8, %rsp`, which keeps the alignment but no longer preserves `%rbx`. To make the damage visible, the caller is written by hand and keeps a live value in `%rbx` across the call.

```{.s include="lab/abi-contract/probe.s" lines="8-14"}
```

```{.output include="lab/abi-contract/run.out" lines="27-28"}
```

Both versions return the right sum and both exit cleanly. Only the caller's own value has changed, from 1000 to 60. In a real program that `%rbx` might hold a loop counter or a pointer, and the failure would show up far from the function that caused it.

The alignment rule fails more loudly. A second version of `sum3` calls a C function, `vector_local`, that GCC compiled at `-O2`.

```{.output include="lab/abi-contract/run.out" lines="30-32"}
```

```{.output include="lab/abi-contract/run.out" lines="35-36"}
```

Do the arithmetic. In the aligned wrapper, `sum3` subtracts 8 before its call, so `vector_local` is entered with `%rsp` at 8 off a boundary, `subq $40` brings it to a multiple of 16, and the `movaps` store to `(%rsp)` lands on an aligned address. The misaligned wrapper skips the subtraction. Now `vector_local` starts on a boundary, subtracting 40 leaves it 8 off, and the store crashes. It died with SIGSEGV in all five attempts. `movaps` requires a 16-byte aligned memory address and faults otherwise [@F44]. GCC emitted it because it trusted the contract.

::: {.aside title="Go does not use this contract"}
Since Go 1.17, Go's compiler on amd64 passes eligible function arguments and results in registers rather than on the stack [@F30; @F51]. Its internal ABI on amd64 uses nine registers for integers, `%rax`, `%rbx`, `%rcx`, `%rdi`, `%rsi`, `%r8`, `%r9`, `%r10` and `%r11` [@F31], and it has no callee-saved registers at all [@F32]. Neither choice matches System V, so Go code and C code cannot simply call each other, and the cgo machinery bridges the two conventions with wrappers and runtime adapters on each crossing [@F52; @F53].
:::

## Reading compiler output

You have now seen enough to learn the rest from the compiler itself, which is how most people who write back ends learn their target. The main tool is `gcc -S`, which stops after compilation proper and writes an assembly file instead of an object file [@F35]. At `-O0`, the default, GCC aims for fast compiles and code that behaves the way a debugger expects [@F36], which is why `n` gets a stack slot here and you can line each statement up with its instructions. At `-O2` it performs nearly all optimizations that do not involve a space-speed tradeoff [@F37].

GCC output can also be full of lines starting `.cfi_`. Those describe an unwind table, a map that lets a debugger or exception handler walk back up the stack from any instruction boundary [@F39]. Passing `-fno-asynchronous-unwind-tables` suppresses them in this lab, which is what the lab did. Chapter 21 returns to unwinding.

Here is the same `fact` at `-O2`.

```{.output include="lab/frames/run.out" lines="23-33"}
```

The recursion is gone. GCC turned it into a loop that keeps the running product in `%rax` and counts `%rdi` down to 1. There is no prologue, no allocated local frame and no `%rbp`. GCC enables frame-pointer omission by default from `-O1` up for functions that do not need one [@F38; @F59], and the psABI allows that, since using `%rbp` as a frame pointer is optional [@F28; @F29]. Without the recursion there is nothing to keep in memory, and everything fits in two registers. How a compiler earns the right to make that change is the business of chapters 14 to 16.

To see the bytes the processor actually runs, use a [disassembler]{.term def="A tool that turns machine code bytes back into assembly text."}. `objdump -d` prints the assembly for every section that should contain instructions [@F40], next to each instruction's offset and encoding.

```{.output include="lab/frames/run.out" lines="47-51"}
```

The `call` encodes as `e8` followed by four zero bytes, because when this object file was written nobody knew yet where `fact` would end up. The line under it is a relocation, a note telling the linker to fill those bytes in later. Chapter 20 explains relocations properly. If you meet Intel syntax elsewhere, `objdump -M intel` switches to it [@F41].

The quickest way to experiment is Compiler Explorer at godbolt.org, a website where you type code in one of dozens of languages and see the compiled output update as you edit [@F42]. Matt Godbolt released it in 2012 [@F43]. Try `fact` there with both `-O0` and `-O2`, then change one line and predict the output before you look.

::: tryit
Copy `lab/frames/fact.c` and change `fact` to take a second argument, `long acc`, so the recursion becomes `return fact(n - 1, acc * n);`, the base case returns `acc`, and `main` starts it with `fact(5, 1)`. Before compiling, predict where `acc` arrives, how big each `-O0` frame now is, and what `&n` spacing gdb will print. Then run `gcc -O0 -S -fno-asynchronous-unwind-tables fact.c`, rebuild the lab executable, and use the lab's gdb script to check.
:::

## What `exprc` was doing all along

Go back to `compute` from chapter 1. It obeyed the System V rules it needed without ever stating them. It left its result in `%rax`, as the convention requires [@F20]. Every `pushq` it made was matched by a `popq`, so `%rsp` held the return address again when `ret` ran. It touched only `%rax` and the other registers it used for arithmetic, none of them callee-saved. And it ended with `ret`, returning to whoever called it.

It got away with ignoring the rest because it had nothing to which they applied. It took no arguments, so the argument registers did not matter. It called nothing, so it needed no stack alignment adjustment before an inner call. It had no locals, so it needed no allocated local frame.

That changes from here. Variables will become stack slots at negative offsets from `%rbp`, starting around chapter 6, and every function your language defines will become a frame with a prologue and epilogue like `fact`'s. Later, chapter 18 chooses the instructions more cleverly and chapter 19 moves values out of stack slots and into registers, which is where the choice between caller-saved and callee-saved registers really matters.

## Check yourself

::: selftest
1. `movl $5, %eax` and `movb $5, %al` both put 5 in the low bits of `%rax`. If `%rax` held `-1` beforehand, what does it hold after each one?
2. Why does GCC's `-O0` `fact` keep `n` at `-8(%rbp)` instead of just leaving it in `%rdi`?
3. A function is entered and immediately executes `call printf` with nothing else before it. Is the stack aligned at that call? What is the smallest fix?
4. In the clobber variant of the lab, the program printed the right sum and exited with status 0. Describe a C caller in which the same bug would produce a wrong answer instead of a silently wrong register.
5. Predict: a function compiled at `-O0` declares a local `long a[3]` in addition to `n`, and calls itself recursively. Would the spacing between activations printed by gdb still be 32 bytes? What determines it?
6. Go's internal ABI has no callee-saved registers. What does that mean for a Go function that keeps a value live across a call, compared with a C function under System V?
:::

::: answers
1. After `movl`, the 32-bit write zero-extends, so `%rax` holds exactly 5. After `movb`, only the low byte changes and the upper 56 bits stay set, so `%rax` holds `0xffffffffffffff05`.
2. `%rdi` is caller-saved and is also where the recursive call's own argument goes, so `n - 1` overwrites it. `n` is needed after the call for the multiply, so it must live somewhere the callee will not touch, which is this activation's frame.
3. No. On entry `%rsp + 8` is a multiple of 16, so `%rsp` is 8 off a boundary, and System V requires it to be on one before `call`. Subtracting 8 from `%rsp`, or pushing one register, fixes it; undo that adjustment before returning. Variadic `printf` also needs `%al` set to an upper bound on the vector registers used.
4. Any caller that keeps a value it needs in `%rbx` across the call, for example a loop counter or an accumulator that GCC placed in `%rbx` because the loop calls `sum3`. After the call that value would be the sum, so the loop would run the wrong number of times or produce a wrong total.
5. Probably not, if GCC allocates space for the array. Each activation's spacing is the return address, the saved `%rbp` and whatever `subq` reserves for locals, rounded so the stack stays 16-byte aligned at the inner call. Adding the 24-byte array may grow that reservation, so inspect the emitted `subq` to see whether the spacing grows to a larger multiple of 16.
6. Any register without a fixed meaning may be destroyed by the call [@F32], so the Go compiler must keep any value it needs afterward in memory, or arrange to recompute it. Under System V the C compiler can instead keep such a value in a callee-saved register and pay only in its own prologue and epilogue.
:::
