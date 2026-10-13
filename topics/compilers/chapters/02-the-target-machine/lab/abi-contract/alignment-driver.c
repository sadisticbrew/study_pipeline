#include <stdio.h>

extern long sum3(long a, long b, long c);
// Separate translation unit: vector_local must materialize its local array.
float read_lanes(const float *lanes) {
    return lanes[0] + lanes[1] + lanes[2];
}
int main(void) {
    printf("sum3(10,20,30) = %ld\n", sum3(10, 20, 30));
    return 0;
}
