// SPDX-License-Identifier: Apache-2.0
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
using Entry = int (__stdcall *)(char*, int, const char*, const char**, int);
std::string quote(const std::string& value) {
    std::string result = "\"";
    for (char c : value) { if (c == '"') result += '"'; result += c; }
    return result + '"';
}
int main(int argc, char** argv) {
    try {
        if (argc != 6) throw std::runtime_error("usage: extension_smoke DLL id session|event body.json expected_status");
        HMODULE module = LoadLibraryA(argv[1]);
        if (!module) throw std::runtime_error("LoadLibrary failed: " + std::to_string(GetLastError()));
        auto entry = reinterpret_cast<Entry>(GetProcAddress(module, "RVExtensionArgs"));
        if (!entry || !GetProcAddress(module, "RVExtensionVersion") || !GetProcAddress(module, "RVExtension"))
            throw std::runtime_error("ABI exports missing");
        char first[64]{}, second[64]{};
        if (entry(first, sizeof(first), "uuid", nullptr, 0) ||
            entry(second, sizeof(second), "uuid", nullptr, 0) ||
            std::string(first).size() != 36 || std::string(first) == second)
            throw std::runtime_error("Per-run UUID generation failed");
        std::ifstream file(argv[4]);
        if (!file) throw std::runtime_error("Cannot open JSON fixture");
        std::string body((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
        auto id = quote(argv[2]), kind = quote(argv[3]), encoded = quote(body);
        const char* args[] = {id.c_str(), kind.c_str(), encoded.c_str()};
        char out[1024]{};
        auto start = std::chrono::steady_clock::now();
        if (entry(out, sizeof(out), "post", args, 3) || std::string(out) != "queued")
            throw std::runtime_error(std::string("Enqueue failed: ") + out);
        auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now()-start).count();
        std::cout << "enqueue_ms=" << elapsed << std::endl;
        if (elapsed > 250) throw std::runtime_error("Enqueue exceeded smoke-test latency budget");
        const char* poll[] = {id.c_str()};
        for (int i = 0; i < 160; ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            if (entry(out, sizeof(out), "poll", poll, 1)) throw std::runtime_error("Poll failed");
            if (std::string(out) == "[-1]") continue;
            std::cout << "result=" << out << std::endl;
            auto expected = "[" + std::string(argv[5]);
            if (std::string(argv[3]) == "command" && std::string(argv[5]) == "200")
                return std::string(out).find(expected + ",[") == 0 ? 0 : 1;
            return std::string(out) == expected + "]" ? 0 : 1;
        }
        throw std::runtime_error("Request did not finish within smoke-test deadline");
    } catch (const std::exception& exc) { std::cerr << exc.what() << std::endl; return 1; }
}
