int first() {
    print(1);
    return 20;
}

int second() {
    print(2);
    return 22;
}

int main() {
    print(first() + second());
    return 0;
}
