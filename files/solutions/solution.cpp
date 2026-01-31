#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long x;
    cin >> n >> x;

    unordered_map<long long, int> pos;
    pos.reserve((size_t)n * 2);

    for (int i = 1; i <= n; i++) {
        long long a;
        cin >> a;
        long long need = x - a;

        auto it = pos.find(need);
        if (it != pos.end()) {
            cout << it->second << " " << i << "\n";
            return 0;
        }
        // keep first occurrence
        if (!pos.count(a)) pos[a] = i;
    }

    cout << "IMPOSSIBLE\n";
    return 0;
}
