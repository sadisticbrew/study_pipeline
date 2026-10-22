# Chapter 1 summary

The reader can trace a matrix coordinate to storage bytes. C arrays contain contiguous elements; typed pointer arithmetic counts elements, while `sizeof` counts bytes. Eight-bit bytes and four-byte `int32_t` are checked lab assumptions. One-past pointer formation differs from dereference, and backing-storage lifetime remains a caller obligation.

A tensor description separates its buffer from metadata: axes, rank, shape, dtype, origin and signed byte strides. Offsets are origin plus the sum of coordinate-times-stride terms. Row-major order changes the last index fastest; contiguity depends on layout and order. Transpose swaps axis descriptions, while positive and negative slices change origin, extent and stride. Views alias their backing storage; materialization creates independent elements. Nonempty reachable-extrema checks must include the whole final element, with arithmetic bounded before evaluation. Numeric validation cannot establish truthful capacity or lifetime.

C-order reshape preserves the logical element sequence, unlike transpose. Some non-contiguous sequences permit metadata-only reshaping, although the lab deliberately accepts fewer cases. Broadcasting matches trailing axes, using equal or size-one extents. Zero strides reuse inputs, not independently writable copies; output storage and arithmetic remain separate costs.

Independent offset/value checks are stronger than equal checksums. The CPU traversal experiment introduces locality, repeated measurements, medians and median absolute deviation, without establishing a universal speedup, isolated hardware cause or GPU result. Chapter 2 builds on byte interpretation and element size to teach floating-point representations; cache cost models remain for chapter 9.
