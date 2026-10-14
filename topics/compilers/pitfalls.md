## 2026-10-13 chapter 2: "zero-extends" used without explanation
- Kind: confusing
- Wrong or unclear: "Writing a 32-bit name zero-extends the result into the whole 64-bit register" used the jargon "zero-extends" with no definition or plain-language explanation, so the learner had to look it up.
- Correct: When an instruction writes a 32-bit register name such as `%eax`, the processor sets the upper 32 bits of the 64-bit register (`%rax`) to zero, so the register holds the 32-bit result with zeros above it. This is zero extension (widening by filling the new high bits with zeros). 8- and 16-bit writes leave the upper 56 or 48 bits unchanged. Say what happens to the bits in plain words before naming the operation, and mark the term.
- Evidence: F4, F5 (Intel SDM Vol. 1, §3.4.1.1, p. 3-12)

## 2026-10-14 chapter 4: parse trees discussed but never drawn
- Kind: confusing
- Wrong or unclear: "One sentence, several trees" asked the learner to draw two parse trees for `10 - 4 - 3 * 2` and listed the lab's five trees only as parenthesized strings, so the chapter talked about parse trees throughout without ever showing one.
- Correct: Under `E → E - E | E * E | num`, the tree worth 0 is `((10 - 4) - (3 * 2))`, with the second `-` at the root and `*` low on the right; the tree worth 6 is `(((10 - 4) - 3) * 2)`, with `*` at the root. Each `E` node's children are the right side of the production that rewrote it, and leaves are `num` tokens. The operator at the root is applied last. When a chapter's central object is a tree or graph, draw at least one with a `.dot` diagram (use small node `width`/`height` so the SVG fits the column at natural size).
- Evidence: F4, F6; lab/grammar-lab/run.out lines 3-9

## 2026-10-14 chapter 2: call/ret, prologue/epilogue and recursive frames described but not drawn
- Kind: confusing
- Wrong or unclear: The chapter explained `call`/`ret`, the `fact` prologue and epilogue, and the five recursive frames only in prose, and its one stack figure was a chain of four boxes ("fact(5) frame: ret addr, saved rbp, n=5") that showed neither the 8-byte slots nor where `%rsp` and `%rbp` point, so the learner had to sketch the stack themselves.
- Correct: `call` pushes the address of the next instruction and jumps, so on entry `%rsp` points at the return address; `ret` pops the top of the stack into `%rip`. After the `-O0` prologue (`pushq %rbp; movq %rsp, %rbp; subq $16, %rsp; movq %rdi, -8(%rbp)`) the frame is, from high to low: return address at `8(%rbp)`, caller's `%rbp` at `0(%rbp)` (where `%rbp` points), `n` at `-8(%rbp)`, an unused slot at `-16(%rbp)` (where `%rsp` points), 32 bytes per activation. `leave` reverses it in two steps (copy `%rbp` to `%rsp`, pop `%rbp`). Every recursive frame's return address is the same `imulq` after `call fact`; the saved-`%rbp` chain is what restores each activation's own `n`. When a chapter's mechanism is a stack layout or register state changing across instructions, draw slot-level snapshots with `%rsp`/`%rbp` marked, as HTML-table `.dot` nodes.
- Evidence: F9, F10, F15, F23, F46, F62 (System V psABI, sec. 3.2.2, figure "Stack Frame with Base Pointer"); lab/frames/run.out lines 4-21, 47-58
