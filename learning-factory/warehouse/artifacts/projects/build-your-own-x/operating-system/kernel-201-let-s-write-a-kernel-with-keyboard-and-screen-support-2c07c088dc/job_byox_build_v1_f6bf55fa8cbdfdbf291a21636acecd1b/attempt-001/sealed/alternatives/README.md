# Alternative: polled input

`polling_input.c` demonstrates a non-interrupt integration using the same pure decoder. Polling avoids
IDT/PIC setup and is useful during bring-up, but consumes foreground time, provides no sleep/wakeup
path, and can still lose controller bytes when other work takes too long. It is an alternative, not
the reference behavior required by R1/R5.

Compile-check it without linking privileged code:

```sh
gcc -m32 -ffreestanding -fno-pie -Wall -Wextra -Werror \
  -Isealed/reference/include -c sealed/alternatives/polling_input.c -o /tmp/polling_input.o
```
