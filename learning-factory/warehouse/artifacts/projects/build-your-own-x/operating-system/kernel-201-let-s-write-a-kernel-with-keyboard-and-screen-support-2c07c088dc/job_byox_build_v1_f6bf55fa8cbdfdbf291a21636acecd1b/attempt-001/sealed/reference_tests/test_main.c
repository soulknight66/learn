#include <stdio.h>

unsigned int test_checks;
unsigned int test_failures;

void run_terminal_tests(void);
void run_keyboard_tests(void);

int main(void)
{
    run_terminal_tests();
    run_keyboard_tests();

    if (test_failures != 0u) {
        fprintf(stderr, "reference tests: FAIL (%u/%u checks failed)\n",
                test_failures, test_checks);
        return 1;
    }
    printf("reference tests: PASS (%u checks)\n", test_checks);
    return 0;
}
