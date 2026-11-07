# FinOps policy (proposal)

Tracked in issue #19. Policy is proposed, not yet implemented.

## Principles
1. **Local-first:** Run the Python director and SQLite alongside an existing Arma server where practical, with a mock provider requiring no cloud credentials.
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
