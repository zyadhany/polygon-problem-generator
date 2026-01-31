#include "testlib.h"
using namespace std;

int main(int argc, char* argv[]) {
    registerValidation(argc, argv);

    int n = inf.readInt(2, 200000, "n");
    inf.readSpace();
    long long x = inf.readLong(-1000000000000000000LL, 1000000000000000000LL, "x");
    inf.readEoln();

    for (int i = 1; i <= n; i++) {
        inf.readLong(-1000000000LL, 1000000000LL, "a[i]");
        if (i < n) inf.readSpace();
        else inf.readEoln();
    }

    inf.readEof();
    return 0;
}
