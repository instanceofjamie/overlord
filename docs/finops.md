# FinOps policy (proposal)

Tracked in issue #19. Policy is proposed, not yet implemented.

## Principles
1. **Local-first:** Run the Python director and SQLite independently of the Arma server, with co-location on a self-managed host only where practical and permitted. Managed hosting (including HostHavoc) may not allow additional processes or native extensions; a mock provider requires no cloud credentials.
2. **Opt-in inference:** Bedrock or another hosted model is optional; no cloud resource is created for ordinary local installation.
3. **Effectively zero cloud idle compute:** Do not run persistent EC2/Fargate, RDS, NAT Gateway, ALB or provisioned model capacity by default. Explicitly justify any such services.
4. **Meaningful events, not game ticks:** Batch observations, compact context, cap deliberation frequency and permit no intervention.
5. **Cheapest adequate model:** Benchmark model quality; deterministic logic should handle routine validation and reactions.
6. **Hard application controls:** Per-session and monthly inference limits, maximum tokens per call, concurrency/rate bounds and conservative in-flight cost reservations. Stop paid inference on exhaustion and fall back safely.
7. **Visible costs:** Report estimated model cost, calls and tokens per session. Configure bounded, redacted logging and retention.
8. **Review every billed addition:** Document projected idle cost, cost per game-hour, usage assumptions and alternative.
9. **Alerts are not hard limits:** AWS Budgets notifications supplement, but do not replace, application controls.

## Initial budget target
Proposed default **£5 cloud AI spend per installation per calendar month**, operator-configurable. A separate smaller per-session limit will be defined before enabling paid inference. This is not yet an enforced ceiling.

## Illustrative inference (not a quote)
4 x 4-hour sessions/month, one model deliberation each 5 minutes = 192 calls. At 3,000 input + 500 output tokens/call and published reference Nova prices, estimated inference only is ~$0.03 Micro, ~$0.06 Lite, or ~$0.46 Pro. Prices vary by region, model and time. Infrastructure, storage, logs, transfer and taxes excluded.

Sources:
- https://aws.amazon.com/lambda/pricing/
- https://aws.amazon.com/api-gateway/pricing/
- https://aws.amazon.com/dynamodb/pricing/
- https://aws.amazon.com/bedrock/pricing/
- https://aws.amazon.com/blogs/machine-learning/effective-cost-optimization-strategies-for-amazon-bedrock/


## Managed game-host compatibility (HostHavoc)

OVERLORD's first real game server is hosted by HostHavoc. **Do not assume OS-level access or permission to run Python alongside Arma.** The Python director can run on a developer PC, independently hosted machine, or optional cloud deployment.

HostHavoc documents custom missions, uploaded mods, launch parameters, and FTP/SFTP. Whether it permits a custom server-side native extension DLL, outbound HTTPS from extensions, or an additional process is **unverified**. Track provider confirmation and proof-of-compatibility in [issue #22](https://github.com/instanceofjamie/overlord/issues/22).

Transport strategy:
1. Prefer a lightweight Arma server-side native extension making async outbound requests **only if HostHavoc permits it**.
2. If server extensions are blocked, design a trusted client relay (e.g. human Zeus machine) with client-side networking and strict server-side `CfgRemoteExec` allowlisting and validation. This requires the relay player to remain connected.
3. Hosting the director in AWS (e.g. usage-billed resources) solves independent orchestration deployment, **not** the game-to-external-world transport. Avoid standing-cost cloud components until justified.

FinOps accounting should separate the existing game-server rental, any relay/device hosting, independent director hosting, and model inference. A director hosted on the user's own PC has no additional cloud standing cost, but depends on that PC being available.

Sources: [HostHavoc hosting](https://hosthavoc.com/en-GB/game-servers/arma-3/), [HostHavoc mods guide](https://demo.hosthavoc.com/en-GB/wiki/game-servers/arma-3/install-workshop-mods), [Arma extensions](https://wiki.arma3.io/topics/Extensions.html), [CfgRemoteExec](https://wiki.arma3.io/topics/CfgRemoteExec.html).


## HostHavoc support update — 2026-11-07 (preliminary)

HostHavoc support reports that there are **currently no restrictions on .dll files for Arma 3 servers**. They say a separately launched executable or service alongside the hosted game server is **likely not possible**. Outbound HTTPS and broader security/hosting policy are being escalated for confirmation. Treat DLL loading as promising but untested, and outbound HTTPS as unconfirmed.

**Current design direction:** a server-side SQF observer/executor with a small asynchronous native extension, communicating outbound to an independently deployed director (local workstation or cloud). Do not require a second process on the HostHavoc machine. Keep the trusted-client relay as a contingency until extension transport is demonstrated.

Host validation still required:
- [ ] Explicit HostHavoc response regarding outbound HTTPS from a DLL in the Arma process and applicable policy
- [ ] Confirm x64 extension actually loads and logs on a test server
- [ ] Confirm an outbound connection and a command round trip without interrupting server frames
- [ ] Confirm deployable DLL file location, updates and server restart process

Source: direct HostHavoc support correspondence supplied by the project maintainer.

## HostHavoc follow-up — 2026-11-07

HostHavoc has now followed up: **"You should be able to use your tool without issue, however, you would not be able to have anything launch alongside the server. For something like that, you would require either a dedicated server or VPS."**

Working interpretation:
- A server-side native extension is acceptable in principle; verify loading, network reachability and callback/polling behaviour in a real game session.
- No separately launched Python executable or service on the HostHavoc game host.
- The director must be independently deployable: developer machine for prototyping, or an optional externally hosted deployment.
- The preferred integration is outbound HTTPS from the native extension; this still requires an empirical end-to-end smoke test, not an assumption of unconditional network access.
- A VPS is an option, **not** a requirement, for the external director. Event-driven services may offer lower idle costs.

This updates the preliminary concerns tracked by [issue #22](https://github.com/instanceofjamie/overlord/issues/22). Preserve a trusted-client relay as fallback only if in-server extension networking fails.
