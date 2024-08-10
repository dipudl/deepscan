#include <stdio.h>

int subtract(int first, int second) {
    return first - second;
}

int main() {
    int i, n;
    int a = 5, b = 2, c, d=7;

    // initialize first and second terms
    int t1 = 0, t2 = 1;

    // initialize the next term (3rd term)
    int nextTerm = t1 + t2;

    // get no. of terms from user
    printf("Enter the number of terms: ");
    scanf("%d", &n);

    // print the first two terms t1 and t2
    printf("Fibonacci Series: %d, %d, ", t1, t2);

    // print 3rd to nth terms
    for (i = 3; i <= n; ++i) {
        printf("%d, ", nextTerm);
        t1 = t2;
        t2 = nextTerm;
        nextTerm = t1 + t2;
    }

    // Arithmetic operators
    c = a / ((b * a) % b);
    d = a * b + c * d;

    subtract(b, a);

    return 0;
}