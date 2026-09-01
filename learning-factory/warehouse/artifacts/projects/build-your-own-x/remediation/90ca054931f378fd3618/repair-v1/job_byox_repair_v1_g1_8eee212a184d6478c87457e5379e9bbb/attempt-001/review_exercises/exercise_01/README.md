# Exercise 01: too-late overflow detection

Review this proposed helper:

```c
static int add_i64(int64_t a, int64_t b, int64_t *out) {
    int64_t sum = a + b;
    if ((b > 0 && sum < a) || (b < 0 && sum > a)) return 0;
    *out = sum;
    return 1;
}
```

Questions:

1. Is the helper valid portable C11 for every pair of `int64_t` values?
2. Can an optimizer invalidate the apparent wraparound check?
3. How would you check the bounds before performing addition?
4. Which exact boundary cases belong in a black-box interpreter test?
