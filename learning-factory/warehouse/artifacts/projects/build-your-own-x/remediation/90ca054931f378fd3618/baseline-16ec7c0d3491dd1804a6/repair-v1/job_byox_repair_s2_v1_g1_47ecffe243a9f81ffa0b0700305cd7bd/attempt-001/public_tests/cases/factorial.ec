int main() {
    int n = 6;
    int result = 1;
    while (n > 1) {
        result = result * n;
        n = n - 1;
    }
    print(result);
    return 0;
}
