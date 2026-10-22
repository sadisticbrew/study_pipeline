#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

_Static_assert(CHAR_BIT == 8 && sizeof(int32_t) == 4, "requires 4-byte int32_t");
int64_t columns_inner(const int32_t *, size_t, size_t);
int64_t rows_inner(const int32_t *, size_t, size_t);
enum { ROWS = 2048, COLS = 2048, WARMUP = 2, TRIALS = 9 };
/* At most 2048*2048*1009 < 2^33, far below INT64_MAX. */
static int64_t now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) { perror("clock_gettime"); exit(1); }
    return (int64_t)t.tv_sec * 1000000000 + t.tv_nsec;
}
int main(void) {
    const size_t n = (size_t)ROWS * COLS;
    int32_t *data = malloc(n * sizeof *data);
    if (!data) return 1;
    for (size_t i = 0; i < n; ++i) data[i] = (int32_t)(i % 1009);
    int64_t reference = columns_inner(data, ROWS, COLS);
    int64_t other = rows_inner(data, ROWS, COLS);
    printf("{\"checksums\":[%" PRId64 ",%" PRId64 "]}\n", reference, other);
    fflush(stdout);
    /* Python independently verifies both results BEFORE releasing timing. */
    char command[16];
    if (!fgets(command, sizeof command, stdin) || command[0] != 't') return 2;
    for (int w = 0; w < WARMUP; ++w) {
        assert(columns_inner(data,ROWS,COLS) == reference);
        assert(rows_inner(data,ROWS,COLS) == reference);
    }
    int64_t overhead[1001];
    for (int i = 0; i < 1001; ++i) { int64_t start=now(); overhead[i]=now()-start; }
    printf("{\"timer_ns\":[");
    for (int i = 0; i < 1001; ++i) printf("%s%" PRId64, i ? "," : "", overhead[i]);
    puts("]}");
    for (int trial = 0; trial < TRIALS; ++trial) {
        for (int position = 0; position < 2; ++position) {
            int order = (trial + position) % 2;
            int64_t start = now();
            int64_t sum = order ? rows_inner(data,ROWS,COLS) : columns_inner(data,ROWS,COLS);
            int64_t elapsed = now() - start;
            assert(sum == reference && elapsed > 0);
            printf("{\"trial\":%d,\"position\":%d,\"order\":%d,\"ns\":%" PRId64 ",\"sum\":%" PRId64 "}\n", trial, position, order, elapsed, sum);
        }
    }
    free(data);
    return 0;
}
