#include <stdint.h>
#include <stddef.h>

/* Separate translation unit, no LTO: calls remain opaque to the caller.
   Interchange/vectorization/unrolling are disabled for BOTH scalar kernels.
   These controls do not guarantee otherwise identical machine instructions or
   isolate a hardware cause. Ordinary loads; out/kernels.s records compilation. */
int64_t columns_inner(const int32_t *data, size_t rows, size_t cols) {
    int64_t sum = 0;
    for (size_t row = 0; row < rows; ++row)
        for (size_t col = 0; col < cols; ++col)
            sum += data[row * cols + col];
    return sum;
}

int64_t rows_inner(const int32_t *data, size_t rows, size_t cols) {
    int64_t sum = 0;
    for (size_t col = 0; col < cols; ++col)
        for (size_t row = 0; row < rows; ++row)
            sum += data[row * cols + col];
    return sum;
}
