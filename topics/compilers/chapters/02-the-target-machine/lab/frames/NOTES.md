# frames lab notes

Expected result: success. Observed result: exit 0 with gcc (GCC) 16.2.1 20260810.

The uninstrumented `fact.c` is used for both assembly listings and the debugger run.
The debugger stops after the argument spill at each entry to `fact`; it converts
addresses to integers before subtracting, rather than subtracting pointers to distinct
C objects. It prints only offsets, so ASLR does not appear in the captured output.
The five offsets are 0, -32, -64, -96, and -128 bytes; the final result is 120.

## Code excerpts (paths relative to the chapter)

- `lab/frames/fact.c`, lines 3-6: the four-line running-example factorial.
- `lab/frames/fact.c`, lines 8-11: the driver calling `fact(5)`.
- `lab/frames/frames.gdb`, lines 4-14: recording the first address and printing
  integer byte offsets at each activation (debugger setup is lines 1-3).

## Captured output excerpts

All ranges below are in `lab/frames/run.out`, inclusive, and at most 20 lines.

| Lines | Observation |
| --- | --- |
| 1-2 | Compiler version used for the observations. |
| 3-21 | `-O0` function: frame-pointer prologue, 16-byte local area, `n` at `-8(%rbp)`, compare/branch, recursive call, multiplication, and `leave; ret`. |
| 22-33 | `-O2` function: multiplication/decrement loop, no recursive call or stack-frame instructions in this emitted function. |
| 34-51 | `objdump -dr` of the `-O0` object: instruction offsets, machine bytes, and the relocation naming `fact` at the call. |
| 52-58 | Five activations at 32-byte decreasing address intervals, followed by `fact(5) = 120`. |

The assembly command uses `-fno-asynchronous-unwind-tables` to suppress `.cfi_`
noise, and `-fcf-protection=none` to omit a control-flow-protection landing pad.
The observer removes non-instruction metadata while retaining local branch labels.
`objdump -dr` is `-d` with relocation records added: the zero call displacement in
this relocatable object is not its final linked target. The relocation names `fact`.

No planned part was dropped. Binaries, objects, and generated assembly live in a
Python temporary directory and are removed on exit. Reproduce from the repo root:

```sh
python3 tools/lab.py run topics/compilers/chapters/02-the-target-machine --only frames
```
