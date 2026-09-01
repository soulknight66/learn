#include <stdio.h>

unsigned int test_failures;

void run_terminal_public_tests(void);
void run_keyboard_public_tests(void);
void run_queue_public_tests(void);

int main(void)
{
    run_terminal_public_tests();
    run_keyboard_public_tests();
    run_queue_public_tests();

    if (test_failures != 0u) {
        fprintf(stderr, "public tests: %u failure(s)\n", test_failures);
        return 1;
    }

    puts("public tests: PASS");
    return 0;
}
