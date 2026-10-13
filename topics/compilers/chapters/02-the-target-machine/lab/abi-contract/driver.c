#include <stdio.h>

extern long probe(long *after);
long echo(long value) { return value; }

int main(void) {
    long after;
    long result = probe(&after);
    printf("sum3(10,20,30) = %ld; caller rbx: 1000 -> %ld\n", result, after);
    return 0;
}
