# abi-contract lab notes

Expected result: success for the enclosing lab. Observed result: exit 0 with gcc
(GCC) 16.2.1 20260810. Child-process failures are captured, not hidden or substituted.

The correct `sum3` receives 10, 20, and 30 in the first three integer argument
registers. It temporarily uses `%rbx`, calls the C function `echo` with an aligned
stack, restores `%rbx`, and returns 60 in `%rax`. The register-violation variant
keeps stack alignment and returns the same sum, but leaves the caller's live
`%rbx` value changed from 1000 to 60. The caller is deliberately written in assembly,
not dependent on gcc choosing a register for a C local. The C driver calls this
assembly probe, which calls each separately linked `sum3` variant.

For the alignment experiment, the aligned wrapper returns 60. The otherwise
identical wrapper compiled with `MISALIGNED` omits the stack adjustment and
terminated with SIGSEGV in five out of five child runs. The real gcc output contains
`subq $40, %rsp` and an aligned `movaps` store to `(%rsp)`. The C callee passes a
local array to a helper in a separate translation unit, so gcc emits the store;
there is no artificial raise, fixed crash instruction, or fabricated result.

## Code excerpts (paths relative to the chapter)

Each excerpt is at most 25 lines. Choose only the pieces needed for the chapter's
90-line total code budget.

- `lab/abi-contract/correct.s`, lines 4-12: working sum3, including save/restore and call.
- `lab/abi-contract/clobber.s`, lines 4-12: the register-violation variant; its stack
  adjustment replaces the save/restore, so this variant breaks only register preservation.
- `lab/abi-contract/probe.s`, lines 4-18: the deterministic assembly caller, including
  its own register saves and aligned call. Lines 8-14 are the essential observation core.
- `lab/abi-contract/driver.c`, lines 3-11: C callback and C driver.
- `lab/abi-contract/alignment.S`, lines 4-12: one source for aligned/misaligned wrappers.
  `MISALIGNED` removes both adjustments, not the call or return.
- `lab/abi-contract/vector.c`, lines 3-8: C callee with an aligned local array and
  a compiler-generated store. `alignment-driver.c`, lines 3-11, supplies the helper/driver.

## Captured output excerpts

All ranges below are in `lab/abi-contract/run.out`, inclusive, and at most 20 lines.

| Lines | Observation |
| --- | --- |
| 1-2 | Compiler version. |
| 3-17 | Assembly source of the correct function. |
| 18-25 | Caller instructions establishing a live 1000 in `%rbx`, passing three arguments, calling, and observing `%rbx`. |
| 26-28 | Correct and clobber variants both return 60 and exit 0; the caller's saved value is respectively 1000 and 60. |
| 29-33 | Actual gcc stack adjustment and instructions around the aligned SSE store in `vector_local`. These are selected non-contiguous instructions, not the whole callee. |
| 34-36 | Aligned wrapper prints 60 and exits 0; misaligned wrapper prints nothing and receives SIGSEGV (returncode -11), five attempts out of five. |

The stack adjustment at the C callee preserves alignment only if its caller obeys
the entry convention. The SSE details are evidence for this experiment, not a new
instruction vocabulary the reader must memorize. Both experiments isolate one rule.

No planned violation was dropped on this machine. On a compiler/platform where the
aligned-store crash does not repeat, the observer explicitly reports that (b) was
dropped and prints each observed status. Core dumps are disabled. All build artifacts
live in a temporary directory and are removed on exit. Reproduce from the repo root:

```sh
python3 tools/lab.py run topics/compilers/chapters/02-the-target-machine --only abi-contract
```
