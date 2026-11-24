# H2332 — native synchronous Normal/off retains the original M1 loan through NPF

H2330 direct queue is separately frozen in H2331 e8d4d3b, run 45311438312 pending behind H2327. Do not dispatch another request until that queue slot starts or completes. H2332 is an independent next source delta, not included in either prior candidate.

The native TX driver is synchronous. When Normal FEC OFF and outer repair OFF (no Auto sender sampler), the original generation-scoped LoanBatch is the entire in-flight authority; the asynchronous Go receipt map has no consumer. Retain the already validated M1 loan across the actual NPF call, then recycle under the original owner after the syscall. Remove all per-source pending insert/remove and FrozenRecord clone/drop pairs from that path. Each real driver disposition still controls copied counters and Health; failed/uncertain bytes burn PN, not resent. Existing cold setter rejects changes while native active. Existing driver/Stop fence retains the loan through the original operation. Go ABI, repair ON, Fixed/Auto and Game keep their original pending/shadow behavior. No new queue, allocation, owner, clock, telemetry, security mechanism or wire change. Added actual original-owner 16/1/8 unit covering frozen wire, no pending, no shadow, reuse and owned Stop. H2332 performance NOT_RUN. Do not infer gain from a smaller operation count.

```feature-impact
{"kind":"none","ids":[],"reason":"Internal synchronous Normal/off first-send loan ownership removes redundant async pending bookkeeping; original repair, FEC, Go ABI and real driver settlement preserved."}
```
