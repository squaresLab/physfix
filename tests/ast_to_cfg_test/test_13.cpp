int test(int x) {
    while (x < 20) {
        if (x % 3 == 1) {
            break;
        } else if (x % 3 == 2) {
            return x;
        } else {
            x += 1;
        }
    }

    return x;
}