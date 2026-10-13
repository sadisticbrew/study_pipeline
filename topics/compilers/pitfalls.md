## 2026-10-13 chapter 2: "zero-extends" used without explanation
- Kind: confusing
- Wrong or unclear: "Writing a 32-bit name zero-extends the result into the whole 64-bit register" used the jargon "zero-extends" with no definition or plain-language explanation, so the learner had to look it up.
- Correct: When an instruction writes a 32-bit register name such as `%eax`, the processor sets the upper 32 bits of the 64-bit register (`%rax`) to zero, so the register holds the 32-bit result with zeros above it. This is zero extension (widening by filling the new high bits with zeros). 8- and 16-bit writes leave the upper 56 or 48 bits unchanged. Say what happens to the bits in plain words before naming the operation, and mark the term.
- Evidence: F4, F5 (Intel SDM Vol. 1, §3.4.1.1, p. 3-12)
