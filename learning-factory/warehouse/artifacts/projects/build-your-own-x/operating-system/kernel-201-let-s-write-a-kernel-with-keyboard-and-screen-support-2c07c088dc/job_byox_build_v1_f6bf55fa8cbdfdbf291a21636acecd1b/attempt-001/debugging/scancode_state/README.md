# Exercise: the sticky extended prefix

A decoder contains this structure (irrelevant mapping code omitted):

```c
if (byte == 0xe0) {
    decoder->extended = true;
    return false;
}
pressed = (byte & 0x80) == 0;
scan = byte & 0x7f;
code = lookup(scan, decoder->extended);
if (code == KEY_CODE_NONE) {
    return false;
}
emit(code, pressed);
return true;
```

Arrow keys sometimes work, but an ordinary key after an arrow or unsupported extended byte can
vanish or be misidentified.

1. Give two minimal input sequences that expose distinct consequences.
2. Identify all return paths relevant to the persistent state.
3. Write a regression test that proves a prefix applies to exactly one following byte.
4. Describe the fix without adding port I/O to the decoder.
