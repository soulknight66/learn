# Debugging lab: the wrong child status

`buggy.c` models a shell that already has a background child when it launches a
foreground child. The program announces both PIDs and then reports a result for
the foreground operation.

From this exercise directory:

```sh
cc -std=c11 -Wall -Wextra -Wpedantic -O0 -g buggy.c -o buggy
./buggy
```

The report is internally inconsistent. Use the PIDs and decoded statuses as
evidence; do not fix the lab by changing the artificial delays.

Questions:

1. What does the return value of each wait function identify?
2. Which children are eligible for the call used at the alleged foreground
   wait?
3. What durable information would a real shell need for several children in one
   foreground pipeline plus unrelated background jobs?
4. How should an asynchronously reaped status reach the code that later asks
   about that job?

Success means foreground status is obtained from the foreground PID regardless
of which background children finish first, and every child is reaped exactly
once.
