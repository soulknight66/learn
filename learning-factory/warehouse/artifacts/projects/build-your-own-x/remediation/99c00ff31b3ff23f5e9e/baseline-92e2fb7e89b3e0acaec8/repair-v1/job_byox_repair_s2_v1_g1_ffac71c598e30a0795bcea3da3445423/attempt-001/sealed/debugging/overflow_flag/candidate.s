# Deliberately buggy fragment for the debugging exercise.
    movq -8(%rbp), %rax
    pushq %rax
    movq -16(%rbp), %rax
    addq -24(%rbp), %rax
    popq %rcx
    jo .Loverflow
    addq %rcx, %rax
    jo .Loverflow
