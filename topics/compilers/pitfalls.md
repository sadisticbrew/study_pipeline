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
