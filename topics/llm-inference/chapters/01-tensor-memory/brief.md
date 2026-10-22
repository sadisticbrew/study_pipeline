# Chapter 1 brief: Tensors are bytes with shapes and strides

Topic: `llm-inference`. Chapter: 1. CD: `topics/llm-inference/chapters/01-tensor-memory`.

This is a learner-approved regeneration. There are no earlier chapters, done or known. Chapter 2 follows with IEEE floating-point representations and assumes byte-addressed storage and element sizes, not the bit-level material itself. `pitfalls.md` is empty. The previous edition's checker report is useful caution, not evidence for fresh factual assertions. Reuse sound lab implementations and current format conventions rather than adding a second implementation.

The chapter-specific state budget is **3000–4500 prose words**, excluding code and answers. It takes precedence over the lab profile's generic range. Target **4200**, allocated below. Preserve depth by cutting side material rather than compressing foundations. No budget increase is needed.

## 1. Starting point

The learner knows variables, loops, arrays, functions, Linux shell use, C and Python, with Go as their main language. They have built systems projects, but general C internals are shaky. They know vectors, matrices, matrix multiplication, numerical precision, basic calculus, two's complement, sets and big-O. Do not reteach linear algebra or calculus.

Byte addresses, element size, typed pointer arithmetic, complete-object bounds, backing-storage lifetime, tensor axes and layouts, broadcasting and a cache model are not established knowledge. Teach the needed C details explicitly. Graph theory, computation DAGs, IEEE fields, masks/shifts, concurrency and GPU execution are unknown and out of scope. Explain locality as an access pattern only, leaving hardware cost models to chapter 9.

There are no earlier summaries or known-chapter mechanisms to reuse. Connect instead to familiar matrix coordinates, nested loops and the concrete difference between sharing element storage and making a new array. Do not assume Go slice internals. The existing topic glossary consists entirely of entries from this very chapter's replaced edition. It does not establish prior learning.

## 2. Crux

How can a program change how it reads an array without moving its values, and how do we determine whether the resulting interpretation is safe or instead requires a copy?

## 3. Opening situation — 120 words including crux

A programmer stores `A=[[0,1,2],[3,4,5]]` in a flat six-element C array and needs the transpose. They change the shape to `(3,2)` and use ordinary row-wise indexing for that new shape. Have the reader predict the first row: `0,1`, not the transpose's `0,3`. The values are still present, but the coordinate-to-storage rule is wrong. Do not introduce an unexplained stride tuple before showing this mismatch. If discussing the alternative of keeping the old row-width calculation, explicitly note that its last row exceeds the six-element array; it is not just a permutation. The example is exact integer storage, not a realistic inference workload. Storage and transpose claims: Q1, Q2, Q7–Q9; numerical examples are derived.

## 4. Sections

Opening/crux 120 + body 3900 + closing/self-test questions 180 = **4200 prose words**. Answers and code/output excluded. Section budgets are targets and may shift within the final range. Use connected explanatory prose, not a vocabulary checklist.

### A. Finding one element means counting bytes — 650 words

Point: derive element indexing from one live C array before asking it to represent a matrix. Explain byte address, element size via `sizeof`, byte offset and typed pointer arithmetic. The lab must verify eight-bit bytes and four-byte `int32_t`; never claim every C `int` has size four. Trace element 5 to offset 20 and its four-byte extent, then distinguish the permitted one-past position from an element that can be read. Explain backing-storage lifetime. Teach only enough character-byte access and `memcpy` to explain why the lab does not dereference an arbitrarily aligned typed pointer.

Builds on: familiar arrays and arithmetic from the profile. Taught here: byte positions versus element counts, whole-object bounds, pointer scaling, backing storage. Trace before showing code. No figure: a small index/value/offset table is clearer.

Likely sources: S35–S42, S62, S63. Claims covered by Q1–Q6.

### B. A shape still needs an indexing rule — 650 words

Point: count complete rows and positions within a row to derive `(i*3+j)*4`. Trace `A[1,2]` to 20 before naming axes, rank, shape, dtype, origin and byte strides. Derive `(12,4)` rather than presenting it as a convention to memorize. Then generalize to origin plus the sum of coordinate-times-stride terms. Distinguish the logical coordinates from byte offsets and a relative origin from an absolute machine address. Explain row-major traversal and contiguity in a stated order. A tensor here means an array with axes, not new tensor algebra.

Builds on: A's element sizes and byte bounds, familiar matrix indexing. New mechanism: several independent coordinate changes contribute to one byte offset. No graph terminology.

Likely sources: S1, S43, S44, S64. Claims Q7–Q8, Q13. Diagram deferred until both layouts exist in C.

### C. A transpose changes the walk, not the buffer — 800 words

Point: require `T[j,i]=A[i,j]`, derive T's shape `(3,2)` and strides `(4,12)`, and trace `T[2,1]` to A's element starting at byte 20. Teach a view and shared-storage aliasing through a mutation that is subsequently restored. A copy has independent elements. Derive a positive slice from start/step/length and a reversed last axis: origin 8, shape `(2,3)`, strides `(12,-4)`. Trace its first row through offsets 8,4,0 before stating negative strides generally.

Safety: logical indices inside shape do not prove arbitrary metadata safe. For nonempty axes, show how each axis contributes its most negative or positive endpoint to reachable minimum/maximum byte offsets, and require the entire element at the maximum to fit. Checked arithmetic must precede potentially overflowing arithmetic. Explain actual lab-supported rank/extent/stride bounds and empty-view handling, without calling this a complete tensor library. Honest capacity, a live backing object, and valid character-pointer provenance remain caller obligations, not consequences of numeric validation. Keep policy choices separate from C rules.

Builds on: A's live storage/bounds and B's coordinate rule. New mechanisms: swapping axis descriptions, stepping and reversing, overlapping descriptions, extent proof.

Diagram plan: one small Graphviz relationship figure shows A and T referring to the same six-element buffer, labeling both shape/stride tuples. Arrows mean shared storage, not element movement or execution dependencies. Highlight one shared element without suggesting the others are not shared. Prose before derives both layouts; prose after traces the highlighted coordinate pair and explains mutation visibility. This is derived layout metadata, not captured x86-64 state, so no instruction snapshot is needed.

Likely sources: S38–S42, S45, S46, S48, S50, S62, S63. Claims Q2–Q6, Q9–Q10.

### D. Reshape preserves a sequence, not a transpose — 600 words

Point: enumerate A in logical row-major order, then group its sequence `0,1,2,3,4,5` into shape `(3,2)`. Contrast T's logical sequence `0,3,1,4,2,5`. Derive from its unequal byte-offset differences why T cannot become one constant-stride axis while preserving the current backing buffer unchanged. A materialized copy can store that sequence consecutively. Explicitly qualify that an in-place data permutation is another operation, not a metadata-only reshape.

Do not claim every non-contiguous view requires a reshape copy: derive a regularly spaced one-dimensional selection reshaped into compatible axes as a counterexample. Distinguish the mathematical possibility of a view, the lab's deliberately conservative reshape policy, and NumPy's documented API. A no-copy procedure can reject layouts a more general one accepts; singleton axes do not generally impose an observable stride requirement. Do not import the whole library algorithm.

Builds on: B's traversal order and C's views. New mechanism: preserving logical element order while changing index grouping. Explicit sequences suffice; no duplicate diagram.

Likely sources: S45, S47, S49, S51. Claims Q11–Q12 and transparent derivations.

### E. Reuse an input value instead of storing repeated rows — 650 words

Point: add `b=[10,20,30]` to A. Trace output `[1,2]` using `A[1,2]` and `b[2]` before teaching broadcasting compatibility. Match trailing axes: extents equal or one is 1; missing leading axes act as 1. Work `(2,3)+(3,)`, reject `(2,)`, and contrast `(2,1)` as a per-row input. A zero stride on the expanded axis derives repeated selection of the same input bytes: `(0,4)` for b expanded to `(2,3)`.

Explain that avoiding repeated input storage does not eliminate output storage or per-output arithmetic and does not promise fewer physical reads. Repeated logical positions are not independently writable. State the lab's read-only policy and NumPy/PyTorch policies separately; do not turn an API recommendation into a universal language restriction.

Builds on: B's axes and C's aliasing. New mechanism: operand-coordinate selection for absent/size-one axes. A short coordinate trace suffices; no second storage-sharing figure.

Likely sources: S43, S48, S52–S55. Claims Q13–Q18.

### F. The same data can take a different route — 550 words

Point: compare row-wise and column-wise visits of the same storage, first on A as byte-offset sequences and then in a bounded CPU benchmark. Define locality as using nearby addresses near one another in time, without presupposing cache lines. Independent exact indexing checks establish layout correctness; equal checksums alone do not prove equal visited multisets or offsets. Benchmark only after correctness, with exact integer reductions sized to avoid overflow.

Interpret only freshly recorded output. Give shape/footprint, compiler flags, one thread, warmup, repeated runs and order, timer overhead, median and a defined dispersion measure, cache-state policy and raw-sample location. Avoid reciting every machine line in prose when the include provides it. Exclude allocation, setup, oracle checks and printing from timed loops. Consumed outputs and transparent optimization controls matter, but do not claim they guarantee identical generated instructions. Count logical input bytes, not measured memory-controller traffic. Reusing an unflushed allocation is not proof the whole buffer is cache resident. Measured CPU timings establish neither a universal traversal ratio nor GPU behavior, nor an isolated causal explanation.

Builds on: A's element extents and B/C's different address walks. New mechanisms: a limited comparison and interpretation of variability, not a complete cache or benchmark methodology chapter.

Likely sources: S32, S56–S61, S65–S66 plus fresh lab output. Claims Q19–Q24. End with byte interpretation/element size as the bridge to chapter 2, without claiming it reuses this exact descriptor.

Closing/self-test questions: 180 words. Include a hand trace and at least one genuinely unseen shape/stride/broadcast prediction. Answers derive the result, not just name it.

## 5. Running example

A is the six-element exact-integer array `0,1,2,3,4,5`, logically `(2,3)`. T is its transpose; a reshape groups A into `(3,2)` without transposing it. Use a positive column slice and reversed columns, a restored shared-storage mutation, and column bias `10,20,30`. Any extra stride-two example is a bounded variant of the same storage. The benchmark enlarges the same two-dimensional traversal problem. Keep all sizes and mutation timing consistent with the actual lab.

## 6. New terms

**No additions relative to the existing glossary are planned.** All current glossary entries belong to the chapter being regenerated, not earlier instruction. Teach and retain/re-establish this chapter's first-use markup for those same chapter-1 terms so the replacement remains standalone and glossary rebuilding remains complete: byte address, element size, byte offset, pointer, buffer, axis, shape, rank, stride, origin, metadata, dtype, tensor, row-major order, contiguous, view, aliasing, slice, reshape, materialization, broadcasting, checksum and locality. Retain median absolute deviation only if the output and prose use it, with a real explanation. Do not duplicate terms in later chapters or introduce extra jargon merely to label the implementation. Familiar matrix/vector operations and numerical precision are not new terms.

## 7. Misconceptions — at most two

1. Changing shape transposes the matrix. Refute using A's reshape and T's distinct logical sequences. Q9, Q11–Q12.
2. Broadcast expansion creates independent writable copies. Refute by showing repeated offsets and explaining the actual write policy. Q15–Q18.

## 8. Fact questions — four scout batches, 24 questions

Facts mode. Each scout has at most **8 searches** and roughly **five minutes**. Prefer existing cached/version-pinned official documentation and source code via the project fetch tool. Read actual evidence this run; old fact records and the previous chapter are not independent evidence. Produce short verbatim quotations and precise locators in the scout JSONL schema. Use source IDs where already present. Never repeatedly chase unavailable book PDFs. Report unanswered questions and any genuinely helpful missing book with title/source identity; no required book is anticipated. No historical claims are requested. All technical claims in this brief are covered below unless explicitly derived in the chapter or defined as a lab-specific contract.

### Batch 1 — C storage and safe access, Q1–Q6

Suggested sources S35–S42, S62 (explicitly a working draft), S63; S2 only if a readable lawful copy is already available. Output `CD/work/scout-1.jsonl`.

1. What does C guarantee about array element contiguity and `sizeof` units, is a C byte universally eight bits, and what does availability of `int32_t` guarantee?
2. How does array subscripting relate to pointer addition, in which units does a typed pointer advance, and how do permitted within-array/one-past pointer formation and permitted reads differ?
3. What object-representation access through character pointers and `memcpy` is permitted? What alignment/effective-type pitfalls prohibit an arbitrary typed load, and how can character traversal cover the complete backing array rather than merely its first element?
4. What backing-object lifetime requirement applies to a non-owning view, and can numeric metadata validation establish lifetime or truthful capacity?
5. What signed-integer overflow rule matters for offsets, and why must bounds-relevant multiplication/addition be checked before evaluation rather than only testing a wrapped final expression?
6. Which documented out-of-bounds/overlap hazards show why valid logical coordinates alone do not establish safety for an arbitrary strided descriptor? Distinguish C rules, a derived nonempty extent proof, and lab policy for unsupported/empty metadata.

### Batch 2 — Layout, views and reshape, Q7–Q12

Suggested S1, S43–S51, pinned NumPy v2.3.0 implementation where necessary. Output `CD/work/scout-2.jsonl`.

7. What components of an ndarray describe the data buffer, shape, dtype/item size, origin/data offset and strides, and which are metadata rather than copied elements?
8. What are byte-stride units and the multidimensional coordinate-offset formula, and what does C order/contiguity mean, including the caveat for axes of length one?
9. What do view, copy and transpose promise about shared storage and mutation visibility, and how is transposition distinct from merely changing shape?
10. How do basic slicing start, step and length change the data origin, axis extent and stride, including a negative step? What warnings apply to overlapping or out-of-buffer stride constructions?
11. What index order does NumPy reshape with `order='C'` preserve, and why is that order distinct from the physical order of a transposed input?
12. When can reshape return a view versus a copy? Find a documented/pinned-source counterexample to 'all non-contiguous inputs must copy', without stretching one adjacent-axis stride condition into a complete sufficient reshape algorithm. Distinguish flatten/ravel policy where mentioned.

### Batch 3 — Axes and broadcasting, Q13–Q18

Suggested S43, S48, S52–S55, S64. Output `CD/work/scout-3.jsonl`.

13. How are axes, rank/dimensionality, shape and dtype/item size defined, without implying floating-point-only storage or new tensor algebra?
14. What is the precise trailing-axis broadcasting compatibility rule, including missing leading axes and incompatible shapes?
15. Which operand coordinate is selected for a size-one or missing axis in a broadcast elementwise operation, and why do `(3,)` and `(2,1)` act differently with `(2,3)`?
16. What documented implementation represents expansion of a size-one axis by stride zero, and does expanding input storage in this way allocate repeated elements?
17. What exact sharing/writeability policy does NumPy `broadcast_to` document, and what in-place-write warning/recommendation does PyTorch `expand` make? Do not conflate their policies.
18. Does avoiding repeated inputs eliminate result storage, arithmetic or necessarily physical reads? Ground what NumPy add does without `out`, and separate the derived storage-count argument from a hardware-traffic claim.

### Batch 4 — Locality and honest timing, Q19–Q24

Suggested S32, S56–S61, S65–S66. Output `CD/work/scout-4.jsonl`.

19. What is spatial locality at the access-pattern level, and how does row/column traversal motivate a comparison without a promised speedup or a detailed cache model?
20. What purposes do warmup/repeated trials serve, and what are the median and median absolute deviation and their limits for interpreting variable timings?
21. What safeguards address optimized-away benchmark work and setup contamination, and what limits remain on claims about generated code or isolated causal explanation?
22. What do `CLOCK_MONOTONIC` and Python `perf_counter` guarantee for interval timing, including possible equal reads and overhead that must be measured locally?
23. Which documented variance/bias sources prevent one CPU ratio from being a general layout law? Avoid privileged tuning requirements and avoid equating an unflushed repeated buffer with proven full cache residency.
24. What environment, compiler/flags, run conditions and raw results should reproducible benchmark reports record? Distinguish counted logical bytes from independently measured hardware traffic and CPU observations from unmeasured GPU claims.

## 9. Lab plan

Required offline **local** CPU labs, expected **success**, no network/root/GPU/proprietary data/extra Python packages. Follow the complete topic lab profile in state.json. Reuse the two existing directories after inspecting their actual implementations. Do not create a parallel convention. Only the lab specialist edits lab code. Run via `tools/lab.py`; do not hand-edit generated output/status. No x86-64 machine-state figures or instruction snapshots are needed.

### `strided-view`

Implement/verify the bounded C strided view against an independently expressed standard-library Python reference. Compare **exact offsets and values**, not just sums, for original layout, transpose, positive/negative slices, reshape versus transpose, zero-stride broadcast addition, shared alias mutation and independent materialization. Reject bad logical indices, false metadata extents and unsafe arithmetic without actually forming/dereferencing invalid pointers. Exercise singleton axes, empty views or clearly documented rejection, negative/zero strides and actual supported rank/domain boundaries. Be explicit about honest capacity, storage lifetime and read-only policy. Do not add floating-point machinery to an integer layout lab. Print compact traces suitable for inclusion and report exact code/output line ranges and any conservative implementation limits.

### `traversal`

Before timing, validate equal-work row/column integer reductions against an independent analytic/Python result on the same deterministic data, supplemented by the layout lab's exact-index evidence. Bounded working set well under 128 MiB. Record CPU/OS, gcc/Python versions, flags, one thread, shape, fixture/input hashes, warmup, repetitions/order, timer and its measured overhead, reuse/cold policy, exact logical work and input bytes, raw samples, median and dispersion. Allocation/setup/checking/printing outside timed loops. Consume outputs; explain optimization controls without claiming more than they guarantee. Keep total run inside the configured timeout. Preserve fresh raw measurements under `out/` or run output, and identify useful short output ranges. Never prewrite timings or conclusions.

Lab handoff must give exact executed commands, success/failure, measured runtime, meaningful code/output line ranges, limitations and what each include proves. Scouts handle external claims; lab evidence handles this implementation and this measured run.

## Writer/checker handoff

`VOICE_EXEMPLAR=style/exemplar.md` is resolved and readable. The writer must read its **entire untruncated contents with tools before BRIEF or drafting**, visibly in the tool transcript. Follow learner/style/format read order. Match its familiar concrete program, failed obvious approach, traced mechanism and connected paragraphs, not its subject or breadth. Do not copy exemplar facts or citations. Only cite chapter facts and freshly captured lab evidence. Omit unanswered factual assertions or mark `[@unverified]`. Observe all code/output/diagram limits. Do not run build/test/format suites during drafting; the requested chapter lint is the bounded writing gate and the orchestrator runs final gates after checking. The checker must verify prose, definitions, equations, table/figure labels, includes, self-tests and answers, and distinguish observed lab contracts from general library/language claims.
