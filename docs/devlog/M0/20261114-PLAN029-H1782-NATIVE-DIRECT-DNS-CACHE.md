# PLAN029 H1782 | Native Direct DNS positive cache, durable FakeIP on hit

- Previous D3 `DnsAnswerCache` existed only as a pure library, not in actual Windows original Rust DNS owner. Wire it inside `DirectDns` (4096 entries/8MiB), keyed by QNAME, A, direct lane, sole DNS IPv4/53 and cold policy revision. Validated positive A from same physical endpoint is memoized with TTL cap/expiry/LRU. Cache miss/full goes through original `DnsPending` and one configured physical socket; no global backpressure, no new resolver or fallback.
- Cached CN A **must** re-run the same all-or-none FakeIP prepare→journal `persist_batch`→synthesize path before Wintun answer. Cache eviction must not discard live FakeIP mappings. No caching NXDOMAIN, NoData, TC truncated or TTL0. The true native unit fixture exercises real journal, original client DNS IDs, same FakeIP on repeated cached answer and no inflight physical socket; no claim of measured real DNS cache throughput yet.
- Original Windows split ingress uses `self.fakes.as_mut()`/`self.journal.as_mut()` to supply the actual writer; no Go DATA callback, no WFP. NonCN Tunnel DNS and D1 TCP53 unchanged. H1781 signed Direct8 Stop Action source locked separately and unaltered by this commit.

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Direct DNS positive cache now actually wired to native owner with FakeIP durability preserved; source-only qualification pending."}
```
