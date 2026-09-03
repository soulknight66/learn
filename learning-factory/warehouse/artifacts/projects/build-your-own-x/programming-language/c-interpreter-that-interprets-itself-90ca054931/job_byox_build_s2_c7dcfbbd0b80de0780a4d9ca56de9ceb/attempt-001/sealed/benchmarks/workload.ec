int main() {
    int i = 0;
    int sum = 0;
    while (i < 10000) {
        store(i % 256, i);
        sum = sum + load(i % 256) % 97;
        i = i + 1;
    }
    print(sum);
    return 0;
}
