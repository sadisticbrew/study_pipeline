---
topic: High-Performance LLM Inference and ML Systems
chapter: 1
title: One block of bytes, many ways to read it
---

Suppose you store the small matrix `A = [[0,1,2],[3,4,5]]` in a C program the usual way, as six integers in one flat array, `0,1,2,3,4,5`, where element `i*3+j` holds `A[i][j]`. Now you need the transpose, which has three rows of two. The quick idea is to declare that the same six numbers are now three rows of two and read row `i`, column `j` at position `i*2+j`. Before reading on, predict the first row you get. It is `0,1`. The transpose's first row is `0,3`. Every value is still in the array, and none was lost, yet the answer is wrong, because the rule that turns a row and column into a position in storage is still the rule for a matrix stored row after row. Keeping the old rule `i*3+j` for the new coordinates is no better, since its last row starts at position `2*3 = 6` and runs past the end of a six-element array.

::: crux
How can a program change how it reads an array without moving its values, and how do we decide whether the new reading is safe or instead needs a copy?
:::

## Finding one element means counting bytes

Before an array can stand for a matrix, we need to be exact about how C finds even one element of a plain array. Take the declaration from the lab, `int32_t data[6] = {0,1,2,3,4,5}`. C promises that an array's elements are allocated contiguously, one after another, and that their number never changes while the array exists [@F1; @F50]. Storage is counted in bytes. Each byte has a [byte address]{.term def="The position of a byte in the program's addressable storage."}, and an array object occupies a run of consecutive bytes [@F90]. The number of bytes one element occupies is its [element size]{.term def="The number of bytes occupied by one stored element."}, and C reports it with `sizeof`, which counts in bytes and gives exactly 1 for the character types [@F51; @F89].

How big is a byte, and how big is an `int32_t`? It is tempting to say eight bits and four bytes, but neither is a universal C rule. A byte has `CHAR_BIT` bits, which is at least eight and may be more [@F2; @F85]. `int32_t`, wherever it exists, is a signed type exactly 32 bits wide with no padding bits [@F3; @F52], so on a machine with eight-bit bytes it takes four. Plain `int` has no such promise, which is why the lab uses `int32_t` and checks both assumptions at compile time. Its first output line records what this machine reported:

```{.output include="lab/strided-view/run.out" lines="1-1"}
```

With four-byte elements we can lay out the whole array as a table. A [byte offset]{.term def="A distance in bytes from a stated starting point."} is measured here from the first byte of `data`:

| Index | Value | Byte offset | Bytes occupied |
|---|---|---|---|
| 0 | 0 | 0 | 0 to 3 |
| 1 | 1 | 4 | 4 to 7 |
| 2 | 2 | 8 | 8 to 11 |
| 3 | 3 | 12 | 12 to 15 |
| 4 | 4 | 16 | 16 to 19 |
| 5 | 5 | 20 | 20 to 23 |

Element 5 starts at offset `5*4 = 20` and covers bytes 20 through 23, and the whole array is 24 bytes. Notice the last column. An element is not a point in storage but an extent of four bytes, and that will matter when we decide what is safe to read.

When you write `data[5]` you never multiply by four yourself. A [pointer]{.term def="A typed value that can refer to an object, a function or just past an array, or be null."} remembers the type it points to, and C defines `data[k]` as `*(data + k)` [@F53; @F86]. Adding `k` to a pointer to an `int32_t` element moves it `k` whole elements along the same array, not `k` bytes [@F4; @F54]. The compiler does the scaling. A pointer to `unsigned char` advances one byte at a time, because a character type has size one [@F5]. So the same storage can be walked in element steps or in byte steps, depending on the pointer's type.

Pointer arithmetic has limits, and they are stricter than many people expect. The result must point at an element of the same array or exactly one past its end, and anything else is undefined behavior the moment the pointer is formed, before any read [@F6; @F60]. The one-past pointer `data + 6` is legal to form and compare, but reading through it with `*` is undefined [@F12; @F55]. So there are three different positions to keep apart. `data + 5` is the last element you can read, `data + 6` is a position you may form but not read, and `data + 7` may not even be computed.

There is also a time limit. An object exists only during its lifetime, and using it, or a pointer to it, after that lifetime ends is undefined [@F10; @F57]. If some description of `data` keeps a pointer to its bytes, the array must stay alive for as long as that description is used. We will call storage that outlives the descriptions reading it a [buffer]{.term def="A region of storage that an array interpretation reads and writes."}.

The lab reads elements at computed byte offsets, so one more C detail decides how it loads them. Converting an `int32_t *` to some other object pointer type is undefined if the result is misaligned for that type [@F87], and a misaligned address is not a valid pointer to dereference [@F56]. Accessing an object through an unrelated type is also undefined, with character types among the allowed exceptions [@F9; @F11]. A character pointer to the whole array addresses its lowest byte, and incrementing it reaches every other byte of that array [@F82]. `memcpy` copies a count of characters, treating both sides as `unsigned char` arrays [@F8], so copying four bytes from the buffer into a real `int32_t` reads an element without any typed load from a computed address. It is also undefined if it runs past the destination or the two regions overlap [@F88].

## A shape still needs an indexing rule

Now let the six integers stand for `A`. Which byte offset holds `A[1,2]`, row 1, column 2? Count what comes before it. Row 0 is complete before row 1 starts, so one whole row of three elements precedes it. Inside row 1, two elements precede column 2. That is `1*3 + 2 = 5` elements, and at four bytes each the element starts at byte `5*4 = 20`, which is the value 5 from the table. For any row `i` and column `j` the count is `(i*3 + j)*4`, and multiplying out gives `i*12 + j*4`.

That rewriting is the whole trick of this chapter. Each coordinate now contributes its own term. Moving down one row adds 12 bytes, and moving right one column adds 4 bytes, independently of where you started. Each independent direction of indexing is an [axis]{.term def="One independently indexed direction of an array."}, numbered from the left, so rows are axis 0 and columns are axis 1 [@F66]. The number of axes is the [rank]{.term def="The number of axes an array has."} [@F104], and the list of counts along them is the [shape]{.term def="The ordered list of element counts along the axes of an array."}, here `(2,3)` [@F67]. The bytes added by one step along an axis is that axis's [stride]{.term def="The signed change in byte offset caused by increasing one axis index by one."}, measured in bytes [@F14; @F62], so `A` has strides `(12,4)`. Nobody chose 12 as a convention. It is three elements of four bytes, the size of one full row.

One more number makes the rule general. The [origin]{.term def="The byte offset reached when every index is zero."} is the offset where index `(0,0)` lives, which for `A` is 0. With it, the offset of any coordinates is

$$\text{offset} = \text{origin} + \sum_k i_k \, s_k,$$

the origin plus each index times its stride. This is the strided scheme NumPy documents for its arrays [@F15]. Check it on `A[1,2]`: `0 + 1*12 + 2*4 = 20`.

Keep two kinds of number apart. Coordinates like `(1,2)` are logical, and they say which element you mean. Offsets like 20 are positions in bytes, measured from the start of the buffer. The origin is also relative to the buffer's first byte, not a machine address. NumPy records the start of an array's data the same way, as an offset within the data buffer [@F61].

Shape, strides, origin and element type describe the bytes without being them. They are [metadata]{.term def="Descriptions of how to interpret stored bytes, as opposed to the values themselves."}. The element type is the [dtype]{.term def="The type and size of each stored element, such as a four-byte signed integer."}, which fixes how many bytes an item takes and how they are interpreted, while the shape fixes the index ranges [@F103]. NumPy describes its array exactly this way, as one data buffer plus information about that buffer, the element size, the start offset, the size of each dimension and the stride of each [@F91; @F92]. In this book a [tensor]{.term def="An array with an ordered set of axes whose coordinates select stored elements."} means nothing more than that: storage plus axes whose coordinates select elements. The lab's C descriptor holds the same fields:

```{.c include="lab/strided-view/view.c" lines="11-17"}
```

Now walk `A` with the last index changing fastest, as nested loops with `j` inside `i` do. The coordinates go `(0,0),(0,1),(0,2),(1,0),(1,1),(1,2)`, which is [row-major order]{.term def="A traversal in which the last axis index changes fastest and earlier axes change more slowly."}, and the offsets come out `0,4,8,12,16,20`. Each step lands on the next element, with no gaps and no repeats. An array whose elements fill consecutive element-sized positions in a stated order like this is [contiguous]{.term def="Laying out an array's logical elements in consecutive element-sized positions, with no gaps, in a stated traversal order."} in that order [@F93]. Contiguity is a property of the metadata and a chosen order together, not of the six integers alone, and the next section shows the same bytes failing it.

## A transpose changes the walk, not the buffer

We can now fix the opening bug without moving a single value. The transpose `T` must satisfy `T[j,i] = A[i,j]`, so its shape is `(3,2)`. What are its strides? Increasing `T`'s first index means increasing `A`'s column index, which adds 4 bytes. Increasing `T`'s second index means increasing `A`'s row index, which adds 12. So `T` is the same buffer with origin 0, shape `(3,2)` and strides `(4,12)`. Trace `T[2,1]`: `0 + 2*4 + 1*12 = 20`, the same element as `A[1,2]`, which is exactly what the transpose requires. NumPy implements transpose this way, changing shape and stride information while the data stays put [@F17].

`T` is a [view]{.term def="An array interpretation that shares another object's storage instead of owning a copy."}, a second description of storage owned by something else. A view is made by changing metadata without changing the buffer, so writes through it show up in the original [@F18]. Two descriptions that reach the same bytes are [aliasing]{.term def="Two or more descriptions that reach the same stored bytes, so a write through one is visible through the other."} each other. The figure shows both descriptions pointing at one buffer:

```{.dot caption="A and T are two descriptions of the same six-element buffer, and both of their coordinates for the highlighted element reach byte 20."}
digraph {
  rankdir=LR; nodesep=0.3; ranksep=0.6;
  node [fontsize=10, shape=box];
  edge [fontsize=10];
  A [label="A\norigin 0\nshape (2,3)\nstrides (12,4)"];
  T [label="T\norigin 0\nshape (3,2)\nstrides (4,12)"];
  buf [shape=record, label="{0 | 1 | 2 | 3 | 4 | <e5> 5}|{byte 0 | byte 4 | byte 8 | byte 12 | byte 16 | <b20> byte 20}"];
  A -> buf:e5 [label="A[1,2]: 12+8 = 20", color=red, fontcolor=red];
  T -> buf:e5 [label="T[2,1]: 8+12 = 20", color=red, fontcolor=red];
}
```

Both arrows land on the same cell, and that is the point to notice: there is one value 5, not two. Every other element is shared in the same way, `T[0,1]` and `A[1,0]` both reaching byte 12 for instance, so a write through either name is a write to the buffer. The lab checks this. It writes 500 through `T[2,1]`, reads it back through `A[1,2]`, and then restores the original 5 before the later examples. It also reads `T` in its own row-major order into a separate array, which makes a copy. A copy duplicates the buffer as well as the metadata, so changing one does not change the other [@F63; @F95]:

```{.output include="lab/strided-view/run.out" lines="2-13"}
```

Line 9 shows `T`'s row-major walk visiting offsets `0,12,4,16,8,20` and reading `0,3,1,4,2,5`, the transpose. Line 13 shows the write appearing through `A` but not in the copy.

Lines 4 and 5 are two more views. A [slice]{.term def="A selection of positions along an axis using a starting index, a stopping point and a step."} picks indices `start, start+step, ...` along one axis, below the stop for positive steps and above it for negative steps [@F48; @F112]. Selecting it moves no elements. NumPy's source moves the data pointer forward by start times the stride, multiplies the stride by the step, and sets the extent to the number of selected indices [@F19; @F96], and every basic slice is a view [@F94]. Take columns 1 and 2 of `A`, start 1, step 1, two indices. The origin becomes `0 + 1*4 = 4`, the column stride stays 4, and the shape is `(2,2)`. That is `S` on line 4, reading `1,2,4,5`.

Now reverse the columns. A negative step walks toward smaller indices, and with no start given it begins at the last index, here 2 [@F20; @F49]. The same three rules give origin `0 + 2*4 = 8`, column stride `4*(-1) = -4`, and three columns, so `R` has origin 8, shape `(2,3)` and strides `(12,-4)`. Trace its first row: `R[0,0]` is at `8`, `R[0,1]` at `8 - 4 = 4`, `R[0,2]` at `8 - 8 = 0`, reading `2,1,0`. Nothing about a negative stride is special. It is a signed step that happens to move toward lower offsets, and it only stays inside the buffer because the origin started high enough.

That last remark is the safety question in miniature. Is it enough to check that each index is inside the shape? No. The shape says which coordinates are legal, but only the strides and origin say where they land. Keep `R`'s strides and set its origin to 0, and `R[0,2]` lands at `0 - 8`, before the buffer, although `(0,2)` is a perfectly legal coordinate. NumPy's `as_strided` warns that arbitrary shapes and strides can point elements at invalid memory and crash the program [@F23; @F98], and that such arrays often overlap themselves [@F24]. Metadata has to be checked against the buffer as a whole.

We can check it without visiting every element. For a nonempty axis with extent `n` and stride `s`, the index runs from 0 to `n-1`, so that axis moves the offset anywhere from 0 to `(n-1)*s`. If `s` is positive, that is the most it can add. If `s` is negative, it is the most it can subtract. Adding every axis's most negative contribution to the origin gives the lowest reachable offset, and adding every positive contribution gives the highest. For `R` the row axis can add `1*12 = 12` and the column axis can subtract `2*4 = 8`, so offsets range from `8 - 8 = 0` to `8 + 12 = 20`. The low end must be at least 0. At the high end, a whole four-byte element must fit, so it must be at most `24 - 4 = 20`. `R` passes. With origin 0 the low end is -8, and it fails. The lab's `valid` is that argument in code:

```{.c include="lab/strided-view/view.c" lines="29-41"}
```

Order matters inside it. Signed overflow in C is undefined, so an overflowed product is not a wrong number that a later test can catch [@F7; @F58], and a compiler may assume it never happens [@F59]. The lab therefore checks rank, origin and capacity first, then each axis's extent and stride before computing that axis's `reach`. Within that domain each product's magnitude is at most `255*65536`, so every sum fits easily in 64 bits. Only then does it form a pointer, by `memcpy` from `storage + byte`:

```{.c include="lab/strided-view/view.c" lines="55-60"}
```

Be clear about which rule is whose. C's rules are the ones about pointers, overflow and lifetime above. The range proof is derived reasoning. Ranks one to three, extents up to 256 and the refusal of empty and scalar views are the lab's own policy, not C's, and the lab is not a complete tensor library. Some things no numeric check can establish. The descriptor cannot tell whether its buffer is still alive, whether `capacity` truthfully states the buffer's size, or whether `storage` came from a character pointer to the whole array. The lab's comments make those the caller's obligations, and its `main` honors them by passing `&data`, the whole array, with `sizeof data`.

## Reshape preserves a sequence, not a transpose

Back to the opening mistake, now with names for it. Changing the grouping of elements is a [reshape]{.term def="A change of shape that preserves the element sequence in a stated traversal order."}. NumPy's C-order reshape reads elements in row-major order and writes them into the new shape in that same order [@F21; @F99], and that order is about indices, not about how memory is laid out [@F100]. So reshaping `A` to `(3,2)` takes the sequence `0,1,2,3,4,5` and groups it in pairs, `[[0,1],[2,3],[4,5]]`. Because `A` is contiguous, that grouping needs only new metadata: origin 0, shape `(3,2)`, strides `(8,4)`, which is line 6 of the output above. The transpose's sequence is `0,3,1,4,2,5`. They are different sequences, and no regrouping of one produces the other.

::: {.misconception title="Changing the shape to (3,2) transposes the matrix"}
C-order reshape keeps the row-major sequence and only regroups it, so `A` reshaped to `(3,2)` starts `0,1`. The transpose reorders the sequence to `0,3,1,4,2,5`, which is the same elements read along a different walk. On line 12 the lab prints both: `reshape(A)` gives `0,1,2,3,4,5` and `copy(T)` gives `0,3,1,4,2,5`. NumPy shows the same thing, flattening a transposed array in its own index order and getting the original's column order [@F26].
:::

Now try the harder direction. Can `T` be flattened to one axis of six elements as a view of the unchanged buffer? A single axis has one stride, so consecutive offsets would have to differ by the same amount every time. `T`'s offsets are `0,12,4,16,8,20`, with differences `+12,-8,+12,-8,+12`. No single stride produces that, so no view of this buffer can present `T`'s sequence on one axis. The way out is [materialization]{.term def="Creating independently stored elements by reading a view in a stated traversal order."}, which reads the view in order into new storage, exactly what produced `copy(T)`. Then the six values sit consecutively and a stride of 4 works. You could also permute the six values inside the original buffer, but that moves data, and it is a different operation from a metadata-only reshape. The lab's `reshape` rejects `T`.

Does every non-contiguous view need a copy to reshape? No, and a counterexample is easy to build. Take every second element of `A`'s buffer as one axis: origin 0, shape `(3,)`, stride 8, reading `0,2,4`. It is not contiguous, since it skips elements. Reshape it to `(3,1)`. The sequence is unchanged, the first axis keeps stride 8, and the new second axis has only index 0. On an axis of length one the only legal index is 0, so its stride never affects any offset and can be anything [@F16]. The lab builds this descriptor by hand:

```{.output include="lab/strided-view/run.out" lines="16-16"}
```

It also says that the lab's own `reshape` rejects this input. That is deliberate. The helper accepts only C-contiguous input, skipping the stride check on length-one axes for the reason just given, and produces a rank-2 result. It is a conservative policy that refuses some layouts a more general procedure could serve. So keep three things apart. Mathematically, a view exists whenever the regrouped sequence can be described by an origin and strides. The lab accepts a narrow subset. With the default `copy=None`, NumPy documents that reshape returns a view when possible and otherwise a copy [@F64; @F27]. Its source attempts a no-copy reshape even when the input is not contiguous in the requested order [@F22; @F101], growing runs of old and new axes until their element counts match and then checking whether those old axes can be combined [@F102], rejecting a group when an adjacent pair of strides fails the C-order relation [@F65]. That is enough to see that "non-contiguous" does not mean "must copy", without reproducing NumPy's whole algorithm here.

## Reuse an input value instead of storing repeated rows

A common step in a model adds a bias vector to every row of a matrix [@F113]. Let `b = [10,20,30]` and compute `A + b` elementwise. What should output `[1,2]` be? Row 1, column 2 of `A` is 5, and the bias for column 2 is `b[2] = 30`, so the answer is 35. Every output row uses the same `b`, and for output `[i,j]` we read `b[j]` no matter what `i` is. The row index of the output is simply ignored when choosing the bias element.

[Broadcasting]{.term def="Matching array shapes for an elementwise operation by reusing input elements instead of copying them."} is the rule that makes this precise for arbitrary shapes. Line the shapes up from the right. Two extents are compatible when they are equal or one of them is 1 [@F28; @F68]. If one shape is shorter, its missing leading axes count as 1, and for nonempty arrays the result takes the larger extent on each axis [@F29].

Our bias shows how the rule plays out. For `(2,3)` and `(3,)`, the trailing 3 matches 3, and the missing axis counts as 1 against 2, so the result is `(2,3)`, and `b` acts like `(1,3)` with the same row read for every output row [@F70]. A bias of shape `(2,)` fails, because its 2 meets the trailing 3 and neither is 1, and NumPy raises an error saying the operands could not be broadcast together [@F33]. A bias of shape `(2,1)` is different again. Its trailing 1 stretches across columns and its 2 matches the rows, so each row gets its own value, read from `[i,0]` for every column [@F69]. The rule is the same, but the operands are placed differently and so act differently.

The strided rule already gives a way to read `b[j]` for every `i` without storing two copies of `b`. If `b` is presented as shape `(2,3)`, the column stride stays 4, and moving down a row must not move at all, so the row stride is 0. With strides `(0,4)`, coordinates `[0,2]` and `[1,2]` both land at offset `0*0 + 2*4 = 8`, which is `b[2]`. PyTorch documents exactly this representation, in which expanding a size-one dimension sets its stride to 0 and allocates no new memory [@F31; @F71]. The lab builds `b` and the row bias the same way:

```{.output include="lab/strided-view/run.out" lines="14-15"}
```

The `(2,1)` row bias gets strides `(4,0)`, the stride of 0 now on the column axis, and `(2,)` is rejected. Notice also what line 14 says the sum is stored in: a separate array. The zero stride saved storing repeated inputs, but every one of the six outputs still needs its own addition and its own place to live. NumPy's `add` returns a freshly allocated array unless you supply `out` [@F35], and the output shape is the common broadcast shape [@F32]. NumPy says broadcasting moves the loop into C and avoids needless copies of data [@F73], and that the stretching is conceptual rather than real copies [@F30]. Saying broadcasting avoids storing copies is a claim about storage. It does not say how many reads reach the hardware, and nothing here measures that.

::: {.misconception title="Broadcasting b to (2,3) gives me six independent elements I can write"}
The expanded `b` has six coordinates but only three stored values, because `[0,j]` and `[1,j]` share offset `4*j`. Writing to `[0,2]` would change `[1,2]` as well. NumPy's `broadcast_to` returns a read-only view in which more than one element may refer to one memory location [@F34]. PyTorch's `expand` returns a view and warns that in-place operations on it may behave incorrectly, recommending a clone before writing [@F72]. These are two libraries' policies, not a law of C. The lab chose to mark any descriptor read-only when an axis expands, so line 7 says `readonly` and its rejection list includes a write through `b`.
:::

## The same data can take a different route

So far every question was about which bytes a description reaches. The last one is about the order it reaches them in. Here are two walks over `A`'s buffer that read every element once:

```{.output include="lab/traversal/run.out" lines="6-6"}
```

The first walks row by row, and each offset is 4 bytes past the last. The second walks column by column, jumping 12 forward and then 8 back. Spatial [locality]{.term def="An access pattern in which nearby storage positions tend to be used close together in time."} is the property the first walk has: most addresses are close to the one accessed just before [@F47]. Caches typically fetch nearby addresses along with the requested one, on the bet that they will soon be needed [@F74], so the first walk might be faster. That is a prediction, not a promise, and chapter 9 builds the actual cost model. Here we only measure.

The lab enlarges `A` to a 2048 by 2048 `int32_t` matrix, 16 MiB, filled with `i % 1009`. Two C functions sum it, identical except for which loop is inside:

```{.c include="lab/traversal/kernels.c" lines="8-22"}
```

`columns_inner` walks row-major. `rows_inner` walks down columns, so each step within a column is 2048 elements, or 8192 bytes. Before timing anything, the lab checks that both compute the right [checksum]{.term def="A summary computed from visited values, used to check that a traversal read the expected data."}, and compares both against an exact sum worked out by formula in Python. Equal sums are evidence, not proof. A broken walk that read element 5 three times and element 0 three times would also total 15 on `A`. That is why the layout lab does not compare sums at all. Its Python oracle builds the key views from nested lists and compares every expected offset and value:

```{.python include="lab/strided-view/check.py" lines="5-19"}
```

Line 20 of the layout output counts what that comparison covered. Only with both checks in hand does timing mean anything. Here is the measurement setup as recorded:

```{.output include="lab/traversal/run.out" lines="1-8"}
```

The protocol follows from what can go wrong. Single timings are noisy and may be unrepresentative, so each order is run repeatedly [@F105; @F38], after warmup runs that are not reported, since early runs may be filling some form of cache [@F37]. The two orders alternate which runs first. Allocation, filling, checks and printing happen outside the timed intervals, so each sample is one visit [@F75; @F108].

The compiler is the other thing to guard against. Every timed result is consumed and checked against the reference, so the sums are part of the program's observable behavior. The kernels sit in a separate file without link-time optimization, and loop interchange, vectorization and unrolling are off for both. These controls limit what the compiler may transform, but they do not guarantee matching instructions, much as a benchmark library's `DoNotOptimize` keeps a result without stopping optimization of the expression that makes it [@F40; @F41]. The generated assembly is kept in `out/kernels.s` for inspection. The clock is `CLOCK_MONOTONIC`, which never goes backwards, although consecutive reads can return equal values [@F76] and frequency adjustments affect it [@F43]. A back-to-back pair of reads took a median of 57 ns here, small beside milliseconds, and the lab does not subtract it.

Now the results:

```{.output include="lab/traversal/run.out" lines="9-16"}
```

The first samples of each order are the slowest, so a mean would be pulled by them. The median, the value with half the samples below and half above [@F106], is based on ranks, and extreme samples distort it less [@F83]. For spread the lab reports the [median absolute deviation]{.term def="The median of the absolute distances between individual samples and their median."}, computed by taking each sample's distance from the median and then taking the median of those distances [@F84], which tail values also influence less [@F107]. The row-major walk has median 3.207 ms with deviation 0.240 ms. The column walk has median 30.259 ms with deviation 3.384 ms. Dividing the medians, the column walk took about 9.4 times as long in this run, and the two ranges do not come near overlapping.

What may we conclude? Both orders specify the same 4,194,304 element reads and additions, so these timings compare loop orders on this machine, with these flags, on this day; they do not isolate a hardware cause. Line 4's 16 MiB of logical reads per visit is counted from the code, not measured traffic, since measuring hardware events needs performance counter support this lab does not use [@F111]. The buffer was reused without flushing, which does not prove it stayed in cache. Scheduling and frequency were not controlled, and cores may not run at the same speed [@F78]. Low noise is necessary but does not rule out bias [@F45], and changing an experimental setup has produced contradictory conclusions in published measurements [@F42; @F36]. So 9.4 is a recorded observation of a scalar CPU loop, not a universal ratio, not a statement about memory bandwidth, and not a prediction for a GPU. Line 18 points to `out/measurements.json`, which holds the raw nanoseconds, hashes and environment, the kind of run context a report should keep [@F109].

::: tryit
Add and emit a descriptor in `main` in `lab/strided-view/view.c` that reverses the rows of `A` instead of its columns. Before running, work out its origin, shape and strides by the slice rules, list its offsets in row-major order, and check by hand that `valid` accepts it. Then add its expected values to `check.py`, using `a[::-1]`, and run the lab.
:::

Everything in this chapter treated an element as four bytes holding an exact integer. Chapter 2 asks how four bytes can instead hold a floating-point number, which needs the same habit of asking how many bytes an element has and how they are read.

## Check yourself

::: selftest
1. Using `R` (origin 8, shape `(2,3)`, strides `(12,-4)`), trace `R[1,0]` to a byte offset and value.
2. Predict the origin, shape, strides and row-major offsets of `A`'s columns 0 and 2 taken with step 2. Is it contiguous?
3. A descriptor of `A`'s 24-byte buffer has origin 4, shape `(2,3)` and strides `(12,4)`. Every index you pass is inside the shape. Should `valid` accept it?
4. Can `R` be flattened in row-major order to shape `(6,)` as a view of the unchanged buffer?
5. Predict the broadcast result shape and operand strides when a `(2,1)` column `c = [100,200]` meets a `(3,)` vector `d`, both stored contiguously. What does output `[1,2]` read? What about `(3,2)` with `(3,)`?
6. A traversal of `A` returns checksum 15. What has it shown, and what has it not?
:::

::: answers
1. `8 + 1*12 + 0*(-4) = 20`, so `R[1,0]` reads the element at byte 20, value 5. This matches row 1 of `R` being `5,4,3`.
2. Start 0 and step 2 leave the origin at `0 + 0*4 = 0`, change the column stride to `4*2 = 8`, and select indices 0 and 2, so shape `(2,2)` and strides `(12,8)`. Offsets are `0,8,12,20`, reading `0,2,3,5`. It is not contiguous in row-major order, since bytes 4 and 16 are skipped. Its reach is 0 to `12 + 8 = 20`, so it is valid.
3. No. The highest reachable offset is `4 + 1*12 + 2*4 = 24`, and a four-byte element there would occupy bytes 24 to 27, past a 24-byte buffer. Legal indices do not make the description safe, and the range check rejects it before any pointer is formed.
4. No. Its row-major offsets are `8,4,0,20,16,12`, with differences `-4,-4,+20,-4,-4`. One axis needs one constant stride, so a materialized copy is needed.
5. Aligning from the right, 1 against 3 gives 3, and 2 against a missing axis gives 2, so the result is `(2,3)`. `c` becomes strides `(4,0)` and `d` becomes `(0,4)`. Output `[1,2]` reads `c[1] + d[2]`, which is `200 + d[2]`. For `(3,2)` with `(3,)`, the trailing 2 meets 3 and neither is 1, so the shapes are incompatible.
6. It shows the visited values sum to the right total, which catches many bugs. It does not show that each element was visited once at the right offset, because reading 5 three times and 0 three times also sums to 15. Comparing each offset and value, as `check.py` does, is the stronger test.
:::
