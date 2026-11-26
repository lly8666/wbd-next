# M0 Dual Rust TCP: Linux Normal scoped product result

Exact SOURCE `86e3ec30010a59cbb60539b902cb96dc21e04d6a`, [run 45809301919](https://github.com/lly8666/wbd-next/actions/runs/45809301919), both native ISA jobs SUCCESS. Evidence: `docs/evidence/M0/20261126-DUAL-RUST-TCP-NORMAL-PRODUCT.json`.

Both native builds run actual original product across four kernel netns, paired explicit Normal/off, client auto-IP / server lease-pool. Each transfers 4 MiB up and 11 MiB down over nine connections; single-stream SHAKE payload hashes, eight concurrent flows (one delayed reader), half-close, UDP echo and both process/owned Stop PASS. Both ZIP digests independently checked with source/architecture, manifest/checksum list and application receipts. Binary bytes are absent from evidence ZIP; no independent binary rehash claim. Server TUN routed 1 on each ISA; queue drops/backpressure zero. FIN-to-first-response 16.55 ms x86_64 / 14.65 ms aarch64 are individual functional observations only.

Original splice stays available. Paired exact-source same-host throughput and CPU, affected modes, reconnect/generation/multi-lease, server-local/source-policy parity, physical and Windows not qualified. Branch inherited governance FAIL is unchanged; main H2451 governance PASS. Next: same-host old splice vs candidate, then affected modes and ownership parity; no product integration or retirement based on this limited pass.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Record actual dual-ISA Normal product qualification only; performance and other modes remain NOT_RUN."}
```
