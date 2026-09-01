int main() {
    int n = 5;
    int product = 1;
    while (n > 1) {
        product = product * n;
        n = n - 1;
    }
    if (product == 120) {
        print(product);
    } else {
        print(0);
    }
    return 0;
}
