# PLAN028 H1247 — shared TUN A backlog recovers without continued full-queue drops

At SOURCE 830d5bc the Linux shared Rust TUN reader receives up to eight kernel packets per turn but retried only one buffered packet per lease, then enqueued new traffic behind backlog. If A was briefly blocked and subsequently consumes eight packets/turn, this one-to-eight imbalance could maintain a full eight-packet pre-copy queue and continue dropping A traffic. This was a code-path risk, **not a measured live loss fraction**.

Change only `v4_embedded_go.rs`: each lease may retry up to eight FIFO buffered packets per reader turn; across leases at most 64 attempts/turn, and stop retrying that lease immediately on `Full` or `Disconnected`. Retain 8 packets/64KiB/100ms, no copy before admission, existing Rust M1 sender and session/generation fences, existing eight TUN receives, no wire/FEC/AEAD change. Tests use the same production `flush_shared_tun` and `enqueue_shared_tun` against real bounded Rust mpsc receivers: both A/B produce eight packets/turn; A blocks for two turns (one bounded overflow), then consumes eight/turn for six turns; require all six full-batch flushes, zero post-recovery overflow, B all 64 correct packet deliveries and FIFO. Existing saturated/age/retire tests run under the same filtered test command.

Targeted one-SOURCE workflow `.github/workflows/m0-plan028-shared-tun-backlog-recovery.yml` on Linux x86_64 native runner; no broad legacy matrix or redundant dispatch. Product full network throughput/CPU and ARM64 not qualified by this unit scenario. H1246 Game2 ARM and x86 two-generation live Actions already SUCCESS (42056882489 / 42056882542) but formal closeout is separate; H998 original same-socket MTU FAIL, other platform/Android NOT_RUN unchanged.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Bounded shared Rust TUN pre-copy backlog now drains up to 8 packets per lease / 64 total attempts per turn; add blocked A→recovered A while B continuous regression, current-SOURCE Action pending."}
```
