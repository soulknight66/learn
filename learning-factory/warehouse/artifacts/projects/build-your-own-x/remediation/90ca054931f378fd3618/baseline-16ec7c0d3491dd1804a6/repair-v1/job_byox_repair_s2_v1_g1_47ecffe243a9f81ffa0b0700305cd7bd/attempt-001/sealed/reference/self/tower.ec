/*
 * A finite bytecode self-interpretation tower.
 *
 * Native mode (arg(0) == 0) interprets bytecode supplied in arg(1...).
 * Simulated ARG maps index zero to one.  Consequently, when this program is
 * given its own bytecode, the nested copy selects the finite marker branch.
 */
int main() {
    int mode = arg(0);
    if (mode != 0) {
        print(4242);
        return 0;
    }

    int pc = 0;
    int sp = 0;
    int running = 1;
    int op = 0;
    int a = 0;
    int b = 0;
    int target = 0;

    while (running != 0) {
        op = arg(pc + 1);
        pc = pc + 1;

        if (op == 0) {
            running = 0;
        } else if (op == 1) {
            a = arg(pc + 1);
            pc = pc + 1;
            store(512 + sp, a);
            sp = sp + 1;
        } else if (op == 2) {
            a = arg(pc + 1);
            pc = pc + 1;
            store(512 + sp, load(a));
            sp = sp + 1;
        } else if (op == 3) {
            a = arg(pc + 1);
            pc = pc + 1;
            sp = sp - 1;
            store(a, load(512 + sp));
        } else if (op == 4) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, a + b);
            sp = sp + 1;
        } else if (op == 5) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, a - b);
            sp = sp + 1;
        } else if (op == 6) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, a * b);
            sp = sp + 1;
        } else if (op == 7) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, a / b);
            sp = sp + 1;
        } else if (op == 8) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, a % b);
            sp = sp + 1;
        } else if (op == 9) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, a == b);
            sp = sp + 1;
        } else if (op == 10) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, a != b);
            sp = sp + 1;
        } else if (op == 11) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, a < b);
            sp = sp + 1;
        } else if (op == 12) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, a <= b);
            sp = sp + 1;
        } else if (op == 13) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, a > b);
            sp = sp + 1;
        } else if (op == 14) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, a >= b);
            sp = sp + 1;
        } else if (op == 15) {
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, -a);
            sp = sp + 1;
        } else if (op == 16) {
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, !a);
            sp = sp + 1;
        } else if (op == 17) {
            pc = arg(pc + 1);
        } else if (op == 18) {
            target = arg(pc + 1);
            pc = pc + 1;
            sp = sp - 1;
            a = load(512 + sp);
            if (a == 0) {
                pc = target;
            }
        } else if (op == 19) {
            sp = sp - 1;
            print(load(512 + sp));
        } else if (op == 20) {
            sp = sp - 1;
            a = load(512 + sp);
            if (a == 0) {
                b = 1;
            } else {
                b = 0;
            }
            store(512 + sp, b);
            sp = sp + 1;
        } else if (op == 21) {
            sp = sp - 1;
            a = load(512 + sp);
            store(512 + sp, load(2048 + a));
            sp = sp + 1;
        } else if (op == 22) {
            sp = sp - 1;
            b = load(512 + sp);
            sp = sp - 1;
            a = load(512 + sp);
            store(2048 + a, b);
        } else if (op == 23) {
            sp = sp - 1;
        } else if (op == 24) {
            sp = sp - 1;
            a = load(512 + sp);
            running = 0;
        } else {
            print(-900);
            running = 0;
        }
    }
    return 0;
}
