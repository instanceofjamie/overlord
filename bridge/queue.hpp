// SPDX-License-Identifier: Apache-2.0
#pragma once
#include <deque>
#include <map>
#include <mutex>
#include <optional>
#include <string>

namespace overlord {
struct Job { std::string id, kind, body; int result = -1; std::string response; };
// The bound covers waiting, in-flight AND completed-but-unread jobs.
class Queue {
    std::mutex mutex;
    std::map<std::string, Job> jobs;
    std::deque<std::string> waiting;
public:
    std::string submit(const Job& job) {
        std::unique_lock<std::mutex> lock(mutex, std::try_to_lock);
        if (!lock.owns_lock()) return "busy";
        if (jobs.count(job.id)) {
            const auto& old = jobs.at(job.id);
            return old.kind == job.kind && old.body == job.body ? "queued" : "invalid";
        }
        if (jobs.size() >= 8) return "full";
        jobs.emplace(job.id, job);
        waiting.push_back(job.id);
        return "queued";
    }
    std::optional<Job> take() {
        std::lock_guard<std::mutex> lock(mutex);
        if (waiting.empty()) return {};
        auto id = waiting.front(); waiting.pop_front();
        return jobs.at(id);
    }
    void complete(const std::string& id, int status, const std::string& response = "") {
        std::lock_guard<std::mutex> lock(mutex);
        jobs.at(id).result = status;
        jobs.at(id).response = response;
    }
    std::string poll(const std::string& id) {
        std::unique_lock<std::mutex> lock(mutex, std::try_to_lock);
        if (!lock.owns_lock()) return "[-1]";
        auto it = jobs.find(id);
        if (it == jobs.end()) return "[-2]";
        int result = it->second.result;
        auto body = it->second.response;
        if (result != -1) jobs.erase(it);
        return "[" + std::to_string(result) + (body.empty() ? "" : "," + body) + "]";
    }
    void discard_completed() {
        std::lock_guard<std::mutex> lock(mutex);
        for (auto it = jobs.begin(); it != jobs.end();) {
            if (it->second.result != -1) it = jobs.erase(it); else ++it;
        }
    }
};
}
