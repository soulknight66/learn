# Review: permission predicate

A translation implementation uses this condition:

```c
if ((mapping->flags & required_flags) == 0u) {
    return -1;
}
```

Review it for requests containing zero, one, or multiple permission bits. Give one concrete mapping
and request that distinguish “any requested permission” from “all requested permissions.”
