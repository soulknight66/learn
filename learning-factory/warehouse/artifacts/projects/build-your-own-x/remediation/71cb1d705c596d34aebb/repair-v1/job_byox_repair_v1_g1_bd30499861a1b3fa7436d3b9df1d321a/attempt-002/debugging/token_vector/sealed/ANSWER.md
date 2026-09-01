# Diagnosis

`capacity` counts `char *` elements, while `realloc` takes a byte count. The
growth call allocates only `capacity` bytes instead of
`capacity * sizeof(**words)`. On a 64-bit host the first growth can even shrink
the allocation, and storing the next pointer writes beyond it.

Compute a checked byte count and keep using a temporary pointer so allocation
failure leaves the original vector valid. Because one slot is reserved for the
NULL terminator, growth must occur before storing when `count + 1` is not less
than capacity. Check the element-count doubling and byte multiplication before
performing either.

`fixed.c` uses `SIZE_MAX` guards, the correct element size, and leaves ownership
with the caller on failure. Reducing the input or disabling AddressSanitizer
only hides the invalid write.
