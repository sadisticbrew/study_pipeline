#include <assert.h>
#include <inttypes.h>
#include <limits.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

_Static_assert(CHAR_BIT == 8 && sizeof(int32_t) == 4, "requires 8-bit bytes and 4-byte int32_t");

typedef struct {
    unsigned char *storage; /* Backing flat array must outlive this descriptor. */
    int64_t capacity, origin;
    int rank;
    int64_t shape[3], stride[3]; /* Byte strides, not element strides. */
    bool readonly;
} View;

/* Caller obligations: storage is character access to the COMPLETE live backing
   array object (use &array, not just &array[0]); capacity is truthful. Numeric
   validation cannot establish provenance, lifetime, or allocated object size.
   memcpy avoids aligned typed loads; this lab stores native int32_t objects.
   Overlap is allowed, not made independently writable; broadcasts are read-only
   when an axis expands. These are lab policies, not a general tensor API. */
/* Domain: rank 1..3, extents 1..256, capacity/origin <=65536,
   |stride| <=65536. Each product <=255*65536; sum < 51 million.
   Arithmetic below is therefore safe in int64_t, BEFORE pointer formation.
   Empty and scalar views are intentionally unsupported; overlap is allowed. */
static bool valid(const View *v) {
    if (!v->storage || v->rank < 1 || v->rank > 3 ||
        v->capacity < 4 || v->capacity > 65536 ||
        v->origin < 0 || v->origin > 65536) return false;
    int64_t low = v->origin, high = v->origin;
    for (int k = 0; k < v->rank; ++k) {
        if (v->shape[k] < 1 || v->shape[k] > 256 ||
            v->stride[k] < -65536 || v->stride[k] > 65536) return false;
        int64_t reach = (v->shape[k] - 1) * v->stride[k];
        if (reach < 0) low += reach; else high += reach;
    }
    return low >= 0 && high <= v->capacity - 4;
}

static bool offset(const View *v, const int64_t index[3], int64_t *out) {
    if (!valid(v)) return false;
    int64_t byte = v->origin;
    for (int k = 0; k < v->rank; ++k) {
        if (index[k] < 0 || index[k] >= v->shape[k]) return false;
        byte += index[k] * v->stride[k];
    }
    if (byte < 0 || byte > v->capacity - 4) return false;
    *out = byte;
    return true;
}

static bool load(const View *v, const int64_t index[3], int32_t *value) {
    int64_t byte;
    if (!offset(v, index, &byte)) return false;
    memcpy(value, v->storage + byte, sizeof *value);
    return true;
}

static bool store(const View *v, const int64_t index[3], int32_t value) {
    int64_t byte;
    if (v->readonly || !offset(v, index, &byte)) return false;
    memcpy(v->storage + byte, &value, sizeof value);
    return true;
}

/* Deliberately narrow API: positive C-contiguous input, rank-2 output.
   This is NOT a general no-copy reshape decision procedure. */
static bool reshape(const View *v, int64_t rows, int64_t cols, View *out) {
    if (!valid(v) || rows < 1 || rows > 256 || cols < 1 || cols > 256) return false;
    int64_t count = 1, step = 4;
    for (int k = v->rank - 1; k >= 0; --k) {
        if (v->shape[k] > 1 && v->stride[k] != step) return false;
        count *= v->shape[k];
        step *= v->shape[k];
    }
    if (count != rows * cols) return false;
    *out = *v;
    out->rank = 2;
    out->shape[0] = rows; out->shape[1] = cols;
    out->stride[0] = cols * 4; out->stride[1] = 4;
    return valid(out);
}

/* Explicit target shape, trailing-axis matching; expanded views are read-only. */
static bool broadcast(const View *v, int rank, const int64_t shape[3], View *out) {
    if (!valid(v) || rank < v->rank || rank > 3) return false;
    View result = *v;
    result.rank = rank;
    for (int k = rank - 1; k >= 0; --k) {
        int source = k - (rank - v->rank);
        int64_t extent = source < 0 ? 1 : v->shape[source];
        if (extent != shape[k] && extent != 1) return false;
        result.shape[k] = shape[k];
        result.stride[k] = source < 0 || extent != shape[k] ? 0 : v->stride[source];
        if (extent != shape[k]) result.readonly = true;
    }
    if (!valid(&result)) return false;
    *out = result;
    return true;
}

/* Logical C-order enumeration; no assumption of contiguous storage. */
static void coordinate(const View *v, int64_t n, int64_t index[3]) {
    for (int k = v->rank - 1; k >= 0; --k) {
        index[k] = n % v->shape[k]; n /= v->shape[k];
    }
}
static int64_t count(const View *v) {
    int64_t n = 1;
    for (int k = 0; k < v->rank; ++k) n *= v->shape[k];
    return n;
}
/* Caller supplies a live, nonoverlapping destination of size int32_t elements;
   size checks the logical count, not the actual destination allocation. */
static void materialize(const View *v, int32_t *out, int64_t size) {
    assert(valid(v) && count(v) == size);
    for (int64_t n = 0; n < size; ++n) {
        int64_t index[3] = {0};
        coordinate(v, n, index);
        assert(load(v, index, &out[n]));
    }
}
static int32_t at(const View *v, int64_t i, int64_t j) {
    int64_t index[3] = {i, j, 0}; int32_t value;
    assert(load(v, index, &value)); return value;
}
static void emit(const char *name, const View *v) {
    assert(valid(v));
    printf("{\"name\":\"%s\",\"origin\":%" PRId64 ",\"shape\":[", name, v->origin);
    for (int k = 0; k < v->rank; ++k) printf("%s%" PRId64, k ? "," : "", v->shape[k]);
    printf("],\"strides\":[");
    for (int k = 0; k < v->rank; ++k) printf("%s%" PRId64, k ? "," : "", v->stride[k]);
    printf("],\"readonly\":%s,\"offsets\":[", v->readonly ? "true" : "false");
    for (int64_t n = 0; n < count(v); ++n) {
        int64_t index[3] = {0}, byte; coordinate(v, n, index);
        assert(offset(v, index, &byte)); printf("%s%" PRId64, n ? "," : "", byte);
    }
    printf("],\"values\":[");
    for (int64_t n = 0; n < count(v); ++n) {
        int64_t index[3] = {0}; int32_t value; coordinate(v, n, index);
        assert(load(v, index, &value)); printf("%s%" PRId32, n ? "," : "", value);
    }
    puts("]}");
}
static void rejected(const char *name, bool accepted) {
    printf("{\"reject\":\"%s\",\"accepted\":%s}\n", name, accepted ? "true" : "false");
}
int main(void) {
    int32_t data[6] = {0,1,2,3,4,5}, bias[3] = {10,20,30};
    int32_t copied[6], result[6], row_bias[2] = {10,20}, row_result[6];
    View a = {(unsigned char *)&data, sizeof data, 0, 2, {2,3}, {12,4}, false};
    View t = a; t.shape[0] = 3; t.shape[1] = 2; t.stride[0] = 4; t.stride[1] = 12;
    View s = a; s.origin = 4; s.shape[1] = 2;
    View r = a; r.origin = 8; r.stride[1] = -4;
    View b1 = {(unsigned char *)&bias, sizeof bias, 0, 1, {3}, {4}, false}, b;
    assert(broadcast(&b1, 2, a.shape, &b));
    View reshaped; assert(reshape(&a, 3, 2, &reshaped));
    materialize(&t, copied, 6);
    View copy = {(unsigned char *)&copied, sizeof copied, 0, 2, {3,2}, {8,4}, false};
    for (int64_t i = 0; i < 2; ++i)
        for (int64_t j = 0; j < 3; ++j) result[i*3+j] = at(&a,i,j) + at(&b,i,j);
    View sum = {(unsigned char *)&result, sizeof result, 0, 2, {2,3}, {12,4}, false};
    emit("A", &a); emit("T", &t); emit("S", &s); emit("R", &r);
    emit("reshape", &reshaped); emit("bias", &b); emit("copy", &copy); emit("sum", &sum);
    int64_t index[3] = {2,1,0}; assert(store(&t, index, 500));
    printf("{\"alias\":[%d,%d,%d]}\n", at(&t,2,1), at(&a,1,2), at(&copy,2,1));
    assert(store(&t, index, 5)); /* Restore the fixture before later examples. */
    emit("restored", &a);
    View rb1 = {(unsigned char *)&row_bias, sizeof row_bias, 0, 2, {2,1}, {4,4}, false}, rb;
    assert(broadcast(&rb1, 2, a.shape, &rb));
    for (int64_t i = 0; i < 2; ++i)
        for (int64_t j = 0; j < 3; ++j) row_result[i*3+j] = at(&a,i,j) + at(&rb,i,j);
    View row_sum = {(unsigned char *)&row_result, sizeof row_result, 0, 2, {2,3}, {12,4}, false};
    emit("row_bias", &rb); emit("row_sum", &row_sum);
    /* A regular step-two sequence can be described as a 3x1 view without a copy.
       Construct that descriptor explicitly: reshape() deliberately rejects it. */
    View step = a; step.rank=1; step.shape[0]=3; step.stride[0]=8;
    View step_matrix = step; step_matrix.rank=2; step_matrix.shape[1]=1; step_matrix.stride[1]=8;
    emit("step", &step); emit("step_matrix", &step_matrix);
    View cube = a; cube.rank=3; cube.shape[0]=1; cube.shape[1]=2; cube.shape[2]=3;
    cube.stride[0]=24; cube.stride[1]=12; cube.stride[2]=4; emit("rank3", &cube);
    View overlap = a; overlap.rank=1; overlap.shape[0]=256; overlap.stride[0]=0; emit("overlap", &overlap);
    View edge = a; edge.rank=1; edge.shape[0]=1; edge.stride[0]=65536; emit("stride_limit", &edge);
    edge.stride[0]=-65536; emit("negative_stride_limit", &edge);
    edge.shape[0]=256; edge.stride[0]=0; edge.origin=20; emit("last_element", &edge);
    /* Singleton strides do not affect the observed sequence or contiguity. */
    View singleton = a; singleton.rank=3;
    singleton.shape[0]=2; singleton.shape[1]=1; singleton.shape[2]=3;
    singleton.stride[0]=12; singleton.stride[1]=-65536; singleton.stride[2]=4;
    emit("singleton", &singleton);
    assert(reshape(&singleton,3,2,&edge)); emit("singleton_reshape", &edge);
    int32_t large[16384] = {0}; large[16383]=42;
    View capacity_edge = {(unsigned char *)&large, sizeof large, 65532, 1, {1}, {0}, false};
    emit("capacity_limit", &capacity_edge);
    int32_t one[1] = {7};
    View capacity_min = {(unsigned char *)&one, sizeof one, 0, 1, {1}, {0}, false};
    emit("capacity_min", &capacity_min);
    int64_t byte;
    index[0]=-1; rejected("negative_index", offset(&a,index,&byte));
    index[0]=2; rejected("index_at_extent", offset(&a,index,&byte));
    index[0]=INT64_MAX; rejected("huge_index", offset(&a,index,&byte));
    index[0]=0; index[1]=3; rejected("second_axis_extent", offset(&a,index,&byte));
    index[1]=0; rejected("readonly_store", store(&b,index,999));
    rejected("transpose_reshape", reshape(&t,3,2,&edge));
    rejected("step_reshape_policy", reshape(&step,3,1,&edge));
    rejected("reshape_count", reshape(&a,2,5,&edge));
    rejected("reshape_huge", reshape(&a,INT64_MAX,6,&edge));
    View incompatible = rb1; incompatible.rank=1; incompatible.shape[0]=2;
    rejected("broadcast_incompatible", broadcast(&incompatible,2,a.shape,&edge));
    rejected("broadcast_lower_rank", broadcast(&a,1,a.shape,&edge));
    rejected("broadcast_rank_four", broadcast(&a,4,a.shape,&edge));
    int64_t empty_target[3]={0,3,0}, huge_target[3]={257,3,0};
    rejected("broadcast_empty", broadcast(&b1,2,empty_target,&edge));
    rejected("broadcast_huge", broadcast(&b1,2,huge_target,&edge));
#define BAD(NAME, FIELD, VALUE) do { View bad=a; bad.FIELD=(VALUE); rejected(NAME,valid(&bad)); } while (0)
    BAD("truncated_element",capacity,23); BAD("tiny_capacity",capacity,3);
    BAD("capacity_domain",capacity,65537); BAD("negative_capacity",capacity,-1);
    BAD("reverse_underrun",stride[1],-4); BAD("origin_one_past",origin,24);
    BAD("negative_origin",origin,-1); BAD("origin_domain",origin,65537);
    BAD("origin_huge",origin,INT64_MAX); BAD("rank_zero",rank,0); BAD("rank_four",rank,4);
    BAD("empty_axis",shape[0],0); BAD("negative_axis",shape[0],-1);
    BAD("dimension_domain",shape[0],257); BAD("huge_dimension",shape[0],INT64_MAX);
    BAD("stride_domain",stride[0],65537); BAD("negative_stride_domain",stride[0],-65537);
    BAD("stride_min",stride[0],INT64_MIN); BAD("stride_max",stride[0],INT64_MAX);
    BAD("positive_reach_overrun",stride[0],65536); BAD("negative_reach_underrun",stride[0],-65536);
    BAD("maximum_origin_one_past",origin,65536);
    BAD("null_storage",storage,NULL);
    return 0;
}
