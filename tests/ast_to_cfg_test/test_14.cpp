int test(int x) {
    while (x < 20) {
        if (x % 3 == 1) {
            break;
        } else if (x % 3 == 2) {
            x += 2;
        } else {
            continue;
        }
    }

    return x;
}