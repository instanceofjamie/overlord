// SPDX-License-Identifier: Apache-2.0
#include "../../bridge/queue.hpp"
#undef NDEBUG
#include <cassert>
int main() {
    overlord::Queue queue;
    for (int i = 0; i < 8; ++i) assert(queue.submit({std::to_string(i), "event", "{}"}) == "queued");
    assert(queue.submit({"overflow", "event", "{}"}) == "full");
    assert(queue.submit({"0", "event", "{}"}) == "queued");
    assert(queue.submit({"0", "event", "changed"}) == "invalid");
    auto job = queue.take(); assert(job && job->id == "0");
    assert(queue.poll("0") == "[-1]");
    queue.complete("0", 201);
    assert(queue.poll("0") == "[201]");
    assert(queue.poll("0") == "[-2]");
    assert(queue.submit({"retry", "event", "{}"}) == "queued");
    job = queue.take(); assert(job && job->id == "1"); queue.complete("1", 0);
    queue.discard_completed(); assert(queue.poll("1") == "[-2]");
}
