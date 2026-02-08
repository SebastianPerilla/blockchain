#include <iostream>
#include <unordered_map>

int main() {
    std::cout << "Collision Found: \n";
    std::unordered_map<int32_t, std::string> seen { { 72, "Sebas" } };

    seen.insert({ 22, "Sebas" });
    seen.insert({ 42, "Sebas" });
    seen.insert({ 29, "Samuel" });

    std::unordered_map<std::string, int32_t> reverse;

    for (const auto &[key, value] : seen) {
        auto [it, inserted] = reverse.emplace(value, key);
        if (!inserted) {
            std::cout << "Keys " << it->second << " and " << key << " both map to \"" << value << "\"\n";
            break;
        }
    }
    std::cout << "Contents:\n";
    for (auto &p : seen) {
        std::cout << ' ' << p.first << " , " << p.second << '\n';
    }

    return 0;
}
