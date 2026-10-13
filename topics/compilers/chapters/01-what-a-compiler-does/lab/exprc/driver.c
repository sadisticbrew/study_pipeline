#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>

extern int64_t compute(void);

int main(void) {
    printf("%" PRId64 "\n", compute());
    return 0;
}
