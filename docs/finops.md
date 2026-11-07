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
