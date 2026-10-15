#include <stdio.h>

long fact(long n) {
    if (n <= 1) return 1;
    return n * fact(n - 1);
}

int main(void) {
    printf("fact(5) = %ld\n", fact(5));
    return 0;
}
