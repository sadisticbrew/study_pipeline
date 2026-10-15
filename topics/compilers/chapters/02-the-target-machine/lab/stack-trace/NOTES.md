# stack-trace lab notes

Expected result: success. Observed result: exit 0 with gcc (GCC) 16.2.1 20260810 and
systemslab 0.1.0.

The same `fact.c` as the frames lab is compiled at `-O0 -g -fcf-protection=none` and run
under `systemslab record`, which single-steps every instruction from `main` to exit and
records each register change and memory write. `--strict` makes the run fail if any
memory change could not be attributed to an instruction or a syscall.

The snapshot point is `fact+0xc@3`: the third time the `cmpq $0x1,-0x8(%rbp)` right
after `fact`'s prologue is about to run. The first two times are `fact(5)` and `fact(4)`;
the third is `fact(3)`, which has just stored its argument `n` at `-8(%rbp)`. At that
step `%rbp` points at the saved `%rbp` slot and `%rsp` at the lowest, still unused slot
of `fact(3)`'s 32-byte frame. Addresses are printed relative to `stack0` (the value of
`%rsp` when `main` started), so ASLR does not appear in the captured output.

`out/stack-fact3.dot` is generated from the same snapshot by `systemslab dot stack` and
is the chapter's stack figure. `out/fact.slt` is the recording; it is not committed.
Open it in the browser viewer with `systemslab view lab/stack-trace` from the chapter
directory.

## Code excerpts (paths relative to the chapter)

- `lab/stack-trace/fact.c`, lines 3-6: the four-line running-example factorial.
- `lab/stack-trace/run.sh`, lines 6-10: compile, record, print the stack, write the
  figure, check the calling convention.

## Captured output excerpts

All ranges below are in `lab/stack-trace/run.out`, inclusive, and at most 20 lines.

| Lines | Observation |
| --- | --- |
| 1 | The program's own output, `fact(5) = 120`. |
| 2-18 | The stack at `fact+0xc@3` (step 28): `main`'s frame collapsed, then three 32-byte `fact` frames, each with return address, saved `%rbp`, `n`, and one unused slot; `%rbp` and `%rsp` marked in `fact(3)`. |
| 5 | `fact(5)`'s return address is the `movq` after `call fact` in `main`. |
| 10, 15 | `fact(4)` and `fact(3)` hold the same return address, `fact+0x2a`, the `imulq` after the recursive call. |
| 6, 11, 16 | The saved `%rbp` values chain the frames: `fact(5)` saved `main`'s frame pointer, `fact(4)` saved `fact(5)`'s, `fact(3)` saved `fact(4)`'s; the last two are 32 bytes apart. |
| 19 | `systemslab check-abi`: no calling-convention violations in the recorded run. |

No planned part was dropped. The binary lives in the lab's temporary directory. Reproduce
from the repo root:

```sh
python3 tools/lab.py run topics/compilers/chapters/02-the-target-machine --only stack-trace
```
