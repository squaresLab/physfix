int test(int x) {
    while (x < 20) {
        if (x % 2 == 1) {
            break;
        } else {
            x += 2;
        }
    }

    return x;
}