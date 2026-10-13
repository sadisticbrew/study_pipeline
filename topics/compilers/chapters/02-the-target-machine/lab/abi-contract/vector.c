#include <xmmintrin.h>

extern float read_lanes(const float *lanes);
long vector_local(long a, long b, long c) {
    _Alignas(16) float lanes[4];
    _mm_store_ps(lanes, _mm_set_ps(0, (float)c, (float)b, (float)a));
    return (long)read_lanes(lanes);
}
