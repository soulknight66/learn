/*
 * A stack-bytecode interpreter written in Mini-C. The outer C implementation
 * interprets this file; this file then interprets the guest program returned by
 * opcode() and operand(). No host opcode or eval shortcut is involved.
 *
 * Guest instruction set:
 *   1 N  push N
 *   2    add the top two values
 *   3    multiply the top two values
 *   4    print the top value
 *   9    halt
 *
 * Guest program: push 6; push 7; multiply; print; halt.
 */

int opcode(int pc) {
    if (pc == 0) return 1;
    if (pc == 1) return 1;
    if (pc == 2) return 3;
    if (pc == 3) return 4;
    if (pc == 4) return 9;
    return 0;
}

int operand(int pc) {
    if (pc == 0) return 6;
    if (pc == 1) return 7;
    return 0;
}

int main() {
    int pc = 0;
    int sp = 0;
    int running = 1;
    int op = 0;
    int arg = 0;
    int left = 0;
    int right = 0;
    int stack0 = 0;
    int stack1 = 0;
    int stack2 = 0;
    int stack3 = 0;

    while (running) {
        op = opcode(pc);
        arg = operand(pc);
        pc = pc + 1;

        if (op == 1) {
            if (sp == 0) stack0 = arg;
            else if (sp == 1) stack1 = arg;
            else if (sp == 2) stack2 = arg;
            else if (sp == 3) stack3 = arg;
            else return 101;
            sp = sp + 1;
        } else if (op == 2 || op == 3) {
            if (sp < 2) return 102;
            if (sp == 2) {
                left = stack0;
                right = stack1;
            } else if (sp == 3) {
                left = stack1;
                right = stack2;
            } else {
                left = stack2;
                right = stack3;
            }
            sp = sp - 1;
            if (op == 2) left = left + right;
            else left = left * right;
            if (sp == 1) stack0 = left;
            else if (sp == 2) stack1 = left;
            else stack2 = left;
        } else if (op == 4) {
            if (sp < 1) return 103;
            if (sp == 1) print(stack0);
            else if (sp == 2) print(stack1);
            else if (sp == 3) print(stack2);
            else print(stack3);
        } else if (op == 9) {
            running = 0;
        } else {
            return 104;
        }
    }
    return 0;
}
