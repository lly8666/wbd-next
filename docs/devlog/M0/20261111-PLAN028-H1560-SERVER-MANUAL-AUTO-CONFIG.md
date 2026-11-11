# PLAN028 H1560 | server default mixed manual+auto leases (2026-11-11)

Resumed exact main SOURCE `dc608f20bdfb5976eba4e73f81041d7d35f8ddaa`; all previous Actions collected. Earlier source620 [mixed Windows/WSL2 Action42942358907](https://github.com/lly8666/wbd-next/actions/runs/42942358907) has two genuine FAIL: loss0 Windows TLS authenticated but Rust TXCopied42/RXDelivered0 and no real 600s, loss30 Windows FakeTCP TLS cold timeout; original files retained. Source dc x86/ARM Game4 and Windows/Linux baseline PASS_SCOPED, not the 5-client mixed test.

**User-reported wiring proven:** server CLI required explicit shared/443 and either a full user-by-user manual /32 mapping **or** auto lease pool, not both. The same server account had no way to run a manually reserved device and a different automatically leased installed device without duplicate /32. The two original shared Normal/Game validators also enforced the false exclusivity.

**Complete cold work package:** server defaults protected TLS shared Normal/Game at port443, owned TUN 10.66.0.1/24 if not explicitly set; derives a bounded auto pool within selected TUN avoiding server and any fixed /32, rejects explicit static/pool overlaps. Optional owner-only 0600 manual mapping may cover a subset of users. Under genuine credential TLS, a manual client only receives its mapped /32 and an automatic client (even with same account) gets the mature 7-day allocator lease using a nonzero installation-derived tunnel ID. No spoofed client-selected IP or new TLS field. No FEC, Game, MTU/outer1460, Health or Rust hot owner rewrite. If client provides no manual IPv4/ID it defaults automatic; omitted manual tunnel ID derives from portable installation. Genuine TLS identity, cert/key, pre-shared route key and raw NIC/source IP remain explicit until OS-bound derivation is proven safe.

**Assembly cross-check:** previous manifest omitted `internal/v4productcli/game_linux.go` and manual account parser test. Both now explicitly source-locked `create` operations, alongside rehashed original Go parser, admission and selector tests. Their running qualification is NOT_RUN until exact-source original x86/ARM Actions execute. Preserve prior first failures.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Shared443 server defaults and authenticated manual per-account static reservation plus disjoint per-installation automatic pool on one Rust TUN; no new TLS/steady record or account bypass."}
```

Evidence [H1560](../evidence/M0/PLAN028-H1560-SERVER-MANUAL-AUTO-CONFIG-20261111.json). PLAN028 remains IN_PROGRESS.
