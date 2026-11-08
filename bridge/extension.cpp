// SPDX-License-Identifier: Apache-2.0
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <winhttp.h>
#include <objbase.h>
#include <cstdio>
#include <chrono>
#include <cstring>
#include <stdexcept>
#include <algorithm>
#include <thread>
#include "queue.hpp"

namespace {
struct Handle {
    HINTERNET value;
    ~Handle() { if (value) WinHttpCloseHandle(value); }
    operator HINTERNET() const { return value; }
};
// No arbitrary URL, proxy, redirects, commands or remote host configuration.
int post(const overlord::Job& job) {
    Handle session{WinHttpOpen(L"OVERLORD-local/0.1", WINHTTP_ACCESS_TYPE_NO_PROXY,
                              WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0)};
    if (!session.value) return 0;
    if (!WinHttpSetTimeouts(session, 1000, 1000, 2000, 2000)) return 0;
    Handle connection{WinHttpConnect(session, L"127.0.0.1", 8000, 0)};
    if (!connection.value) return 0;
    const wchar_t* path = job.kind == "session" ? L"/v1/sessions" : L"/v1/observations";
    Handle request{WinHttpOpenRequest(connection, L"POST", path, nullptr,
                                     WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, 0)};
    if (!request.value) return 0;
    DWORD policy = WINHTTP_OPTION_REDIRECT_POLICY_NEVER;
    if (!WinHttpSetOption(request, WINHTTP_OPTION_REDIRECT_POLICY, &policy, sizeof(policy))) return 0;
    const wchar_t* headers = L"Content-Type: application/json\r\n";
    if (!WinHttpSendRequest(request, headers, (DWORD)-1, (void*)job.body.data(),
                            (DWORD)job.body.size(), (DWORD)job.body.size(), 0) ||
        !WinHttpReceiveResponse(request, nullptr)) return 0;
    DWORD code = 0, size = sizeof(code);
    if (!WinHttpQueryHeaders(request, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                             WINHTTP_HEADER_NAME_BY_INDEX, &code, &size, WINHTTP_NO_HEADER_INDEX)) return 0;
    // API 200/201 acknowledges a committed record. Never read unbounded response bodies.
    return (int)code;
}
struct Bridge {
    overlord::Queue queue;
    Bridge() {
        // Arma may retain this DLL between missions. Pin it and keep one process-lifetime worker;
        // never join a worker under the Windows loader lock or unload code underneath it.
        HMODULE module;
        if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                               GET_MODULE_HANDLE_EX_FLAG_PIN,
                               reinterpret_cast<LPCSTR>(&post), &module))
            throw std::runtime_error("Cannot pin bridge");
        std::thread([this] {
            for (;;) {
                if (auto job = queue.take()) {
                    try { queue.complete(job->id, post(*job)); }
                    catch (...) { queue.complete(job->id, 0); }
                } else std::this_thread::sleep_for(std::chrono::milliseconds(50));
            }
        }).detach();
    }
};
Bridge& bridge() { static auto* instance = new Bridge; return *instance; }
void output(char* dest, int size, const std::string& text) {
    if (size <= 0) return;
    const auto count = (std::min)(text.size(), (size_t)size - 1);
    memcpy(dest, text.data(), count); dest[count] = '\0';
}
// Default RVExtensionArgs strings are SQF-quoted; accept raw harness input too.
std::string argument(const char* value) {
    std::string text(value);
    if (text.size() < 2 || text.front() != '\"' || text.back() != '\"') return text;
    std::string decoded;
    for (size_t i = 1; i + 1 < text.size(); ++i) {
        if (text[i] == '\"') {
            if (i + 2 >= text.size() || text[i + 1] != '\"')
                throw std::runtime_error("Invalid SQF string");
            ++i;
        }
        decoded += text[i];
    }
    return decoded;
}
bool valid_id(const std::string& id) {
    if (id.size() != 36) return false;
    for (size_t i = 0; i < id.size(); ++i) {
        if (i == 8 || i == 13 || i == 18 || i == 23) { if (id[i] != '-') return false; }
        else if (!((id[i] >= '0' && id[i] <= '9') || (id[i] >= 'a' && id[i] <= 'f'))) return false;
    }
    return true;
}
}
extern "C" __declspec(dllexport) void __stdcall RVExtensionVersion(char* out, int size) {
    output(out, size, "OVERLORD local observation bridge 0.1");
}
extern "C" __declspec(dllexport) void __stdcall RVExtension(char* out, int size, const char*) {
    output(out, size, "Use RVExtensionArgs: post, poll, reset");
}
extern "C" __declspec(dllexport) int __stdcall RVExtensionArgs(
    char* out, int size, const char* function, const char** args, int count) {
    try {
        std::string command(function);
        if (command == "uuid" && count == 0) {
            GUID guid;
            if (FAILED(CoCreateGuid(&guid))) throw std::runtime_error("UUID failed");
            char text[37];
            std::snprintf(text, sizeof(text),
                "%08lx-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x",
                guid.Data1, guid.Data2, guid.Data3,
                guid.Data4[0], guid.Data4[1], guid.Data4[2], guid.Data4[3],
                guid.Data4[4], guid.Data4[5], guid.Data4[6], guid.Data4[7]);
            output(out, size, text); return 0;
        }
        std::string id = count > 0 ? argument(args[0]) : "";
        std::string kind = count > 1 ? argument(args[1]) : "";
        std::string body = count > 2 ? argument(args[2]) : "";
        if (command == "post" && count == 3 && valid_id(id) &&
            (kind == "session" || kind == "event") &&
            body.size() <= 2048) {
            output(out, size, bridge().queue.submit({id, kind, body})); return 0;
        }
        if (command == "poll" && count == 1 && valid_id(id)) {
            output(out, size, bridge().queue.poll(id)); return 0;
        }
        if (command == "reset" && count == 0) {
            bridge().queue.discard_completed(); output(out, size, "ready"); return 0;
        }
        output(out, size, "invalid"); return 1;
    } catch (...) { output(out, size, "unavailable"); return 2; }
}
