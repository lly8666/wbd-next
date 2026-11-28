# H2547 — accept seeded BBR1/BBRv3 long-flow results

Exact cdd60c2 native46134184084 and three ARM46134184014 SUCCESS, six evidence ZIP CRC clean. Both ISA 362 core/7 native functional profiles, including actual BBR3 seed/service; ARM local normal/pause/weak measured. Both long arms hash/EOF/joined Stop/natural bulk retirement, actual seed and mode valid. Identical ARM manifest, no netem drops. See docs/evidence/M0/20261128-L2-BBR1-BBR3-180S-SEED-RESULT.json.

B/V first180 399.21/385.34Mbps, retired retrans0.4107/0.2740%, RTO2/0, recoveries86/68, endpoint CPU29.95/31.50 CPU-s/GiB, host85.77/90.62; client ingress1950/0, server0/0. 30s rate B333.97/423.70/424.11/415.30/398.96/399.21 versus V349.32/385.50/394.67/393.78/393.62/395.17; P10 105.55/128.75M, seconds below50M 10/4. Forward sampled cross-host gaps551/349 of136992/131255, no other adjacent differences, no capture kernel drops. Forward only, no physical loss attribution. B server publish peak32 vs V64: peak batch alone not sufficient cause of pressure. BBR3 ProbeRTT retains about12–13MB cwnd versus BBR1 4196B. H2545 BBR1 severe post-ProbeRTT collapse not reproduced on H2546 BBR1. BBR3 preferable stability candidate, not proven general winner. One order, no causal performance PASS.

H2545 four-arm history retained FAIL waiter with all four client measurements. Old Rust CUBIC291.69M/0.0105%/43.36 CPU; splice215.99M/26.54; BBR1 311.30M/0.804%/33.26. Different runner/path, no causal cross-run delta or CPU parity. Both current BBR arms still above historical splice CPU, but same-host splice comparison remains needed. No new run, no runtime/default/wire change. L2 OPEN; prioritize common service/EDT timing and ACK CPU, keep BBR1/3 competitive rather than tuning arbitrary caps. Main H2546 scope audit failed unbounded context_refs; bound next cursor without changing governance policy.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Accept actual matched 180s diagnostic and scoped dual ISA native evidence; preserve historical failure, no default or L2 promotion."}
```
