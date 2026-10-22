15 chapter findings fixed: miscited 0, stretched 2, unsupported 2, contradicted 5, output mismatch 0, misleading simplification 6; stretched facts 4 narrowed; unresolved/unverified 0.

## Findings

Line numbers refer to the precheck draft and remain unchanged. The table records original → resolved wording or behavior; unaffected claims were left alone.

| Line | Category | Original → resolved | Evidence |
|---|---|---|---|
| 15 | misleading simplification | “object” → “array object”; avoids applying the byte-sequence rule to bit-fields. | F90 |
| 41 | contradicted | `memcpy` undefined “only if” destination overflow/overlap → “also”; source validity still matters. | F82, F88; N3220 §7.1.4, §7.26.2.1 |
| 90 | stretched | Every slice stays “below” stop → below for positive, above for negative steps. | F48, F112; [Python sequence operations](https://docs.python.org/3/library/stdtypes.html#common-sequence-operations) |
| 90 | unsupported | “Nothing but arithmetic on metadata” → “moves no elements”; no allocation/cost guarantee. | F94, F96; S50 `mapping.c:894–904` |
| 101 | contradicted | All fields checked before any reach → global checks, then each axis before its reach. | `lab/strided-view/view.c:29–40` |
| 113 | misleading simplification | “Reshape keeps row-major sequence” → “C-order reshape”; other orders are not excluded. | F99, F100 |
| 123 | misleading simplification | NumPy always returns view-if-possible → explicitly scopes that policy to default `copy=None`. | F27, F64; [NumPy reshape](https://numpy.org/doc/2.3/reference/generated/numpy.reshape.html) |
| 127 | unsupported | Uncited model bias example → cites primary affine-layer definition. | F113; [PyTorch Linear](https://docs.pytorch.org/docs/2.9/generated/torch.nn.Linear.html) |
| 129 | misleading simplification | Larger-extent output rule → restricted to nonempty arrays, avoiding zero-extent overgeneralization. | F29, F67 |
| 156 | contradicted | Every column-order step is 8192 bytes → each step within a column. | `lab/traversal/kernels.c:16–21` |
| 156 | contradicted | Every oracle view comes from nested lists → key views do; every offset/value is compared. | `lab/strided-view/check.py:5–34,48–52` |
| 177 | stretched | Timing difference “comes from” access order → compares loop orders, without isolating hardware cause. | `lab/traversal/kernels.c:4–7`; `lab/traversal/run.out:13–16`; F45, F78 |
| 180 | contradicted | Add a descriptor and expectation → also emit it, as the checker requires. | `lab/strided-view/view.c:130–146,166–167`; `lab/strided-view/check.py:42–61` |
| 191 | misleading simplification | Unspecified flattening order → explicit row-major order, matching the answer's offset trace. | Chapter 200; F99, F100 |
| 192 | misleading simplification | Ambiguous result “strides” → operand strides, matching the answer rather than output-storage strides. | Chapter 201; `lab/strided-view/view.c:158–165` |
| 41 / F11 | stretched fact | “Only compatible or character types” → listed effective-type exceptions; removed an unjustified exhaustive list. | F11 verbatim quote; F9 |
| 57 / F91 | stretched fact | Buffer unconditionally contiguous/fixed → restores the quote's “typically”. | F91 verbatim quote |
| 90 / F97 | stretched fact | Generic below-stop rule → positive-step slices only. | F97 verbatim quote; F112 |
| 177 / F111 | stretched fact | Generic hardware-counter build/libpfm requirement → Google Benchmark's documented feature only. | F111 verbatim quote, S67 |

## Coverage and evidence

- Reviewed all 53 prose paragraphs printed by `claims.py`, not a sample, including uncited claims, asides, misconception blocks, definitions, the byte table, offset equation, all diagram nodes/edges/labels/caption, exercises, and all six self-test questions and answers. Judgments used verbatim fact quotations rather than scout summaries.
- Read `pitfalls.md` (empty), the complete roadmap, both recorded `run.out` files and success statuses, the complete final layout C/Python sources, and traversal kernels, timing C, measurement Python, and compiler flags. Read retained measurement context and the primary NumPy reshape/slicing implementation sections where API policy and metadata costs mattered.
- Every existing include range is within its source and matches its surrounding interpretation: layout C 11–17, 29–41, 55–60; layout output 1, 2–13, 16, 14–15; oracle 5–19; traversal kernels 8–22; traversal output 6, 1–8, 9–16. All includes and `.term` markers were preserved; the hand-authored diagram needed no factual change.
- Layout output line 20 records **22 descriptors, 604 offset comparisons, 604 value comparisons, one alias event, and 37 rejections**. The prose's line-20 reference is correct; there were no stale numerical counts to replace. Capacity/extent/stride limits, singleton-axis treatment, complete-array character provenance, truthful live backing storage, aliasing, copy independence, and read-only broadcast policy agree with the final code and recorded output.
- Traversal output lines 9–12 support medians **3.207 / 30.259 ms**, MADs **0.240 / 3.384 ms**, and the approximately **9.4×** median ratio. The shown sample extrema do not overlap; each order's first sample is its slowest. The 57 ns timer-pair median, 16 MiB buffer/logical-read count, checksums, warmup/repetition counts, compiler controls, and metadata paths match recorded evidence. Logical accesses are not claimed as measured hardware traffic; warmup does not establish full residency; equal checksums do not establish identical visits; CPU timings do not establish GPU behavior.
- Added primary-source facts **F112–F113**, sources **S68–S69**, through `work/checker.jsonl` and `state.py merge`. Narrowed **F11, F91, F97, F111** through `state.py fact`; no source quotations were rewritten. Existing F27 supplied the reshape copy-policy evidence, so no duplicate fact was added.
- The C normative reference is expressly **N3220, the January 2024 working draft**, not a claim to have inspected the final published standard.

## Limits and unresolved claims

No unresolved or `[@unverified]` claims remain from this review. This was source/output inspection and hand-checked arithmetic, not a new execution of either lab. No tests, builds, lint, formatting, freshness checks, or rendering were run. Existing success statuses were read, not independently reproduced. The parent owns final gates.

Only chapter factual wording, this report, and allowed evidence records/cache were changed; lab inputs/output, summary, brief, and generated state documents were not edited. The raw whitespace-word count increased by 26 versus the preserved draft; the supplied 4418-word prose baseline therefore retains headroom under 4500, but the exact pipeline prose counter was not rerun. Elapsed review time: approximately 7 minutes.

## Human flags

- Parent: run the final prose-budget, lint, freshness, and render gates; none was exercised here.
- No remaining factual doubts identified; omitted ravel/flatten and alternative reshape-order API details remain intentionally outside this chapter.
