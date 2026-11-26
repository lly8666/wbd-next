# M0 matched CUBIC and mixed BBR same-VM ABBA result

User request: unify congestion algorithm before attributing CPU. SOURCE f2b88695d062556fdb804c69041705beb5b64280, run45815349231, same x86 VM boot 21fb92dd-4175-40ed-b979-aeda9950013d. Actual three build manifests and measurement ZIP reviewed, see docs/evidence/M0/20261126-DUAL-RUST-TCP-CC-MATCHED-ABBA.json. Kernel in-tree tcp_bbr module srcversion 5B6C12777290291DF28F230, file SHA256 recorded; metadata does not identify exact BBR generation. pktkit bbr.rs explicitly draft-ietf-ccwg-bbr-06 BBRv3. Matched CUBIC both Rust endpoints and all kernel namespaces, old accepted socket and iperf sender/receiver CC read back. Algorithm match, not identical implementation. Mixed BBR reference on same VM immediately following CUBIC ABBA; different block order/time remains a limitation.

| 25s clean download | old splice | dual Rust | B/A |
| --- | ---: | ---: | ---: |
| CUBIC Mbps | 573.745 | 573.830 | +0.015% |
| CUBIC client CPU-s/GiB | 7.821 | 11.532 | +47.45% |
| CUBIC server CPU-s/GiB | 9.474 | 8.775 | -7.38% |
| CUBIC host CPU-s/GiB | 20.433 | 23.537 | +15.19% |
| Mixed BBR Mbps | 570.979 | 573.553 | +0.45% |
| Mixed BBR client CPU-s/GiB | 7.859 | 11.792 | +50.05% |
| Mixed BBR server CPU-s/GiB | 9.568 | 9.144 | -4.43% |
| Mixed BBR host CPU-s/GiB | 20.586 | 24.094 | +17.04% |

CUBIC client RX 6.528 -> 5.078 CPU-s, TX 4.522 -> 11.398 CPU-s. TUN reverse packet count 457591 -> 1043279 (+128%); actual outer first-copy record count 457591 -> 700643.5 (+53.1%), outer first-wire bytes 56.28M -> 86.18M; outer RX data_unique only +1.93%. Mixed BBR same direction: TUN 468930.5 -> 1016313 (+116.7%), outer first copy 468930.5 -> 705564.5 (+50.5%), RX unique +2.50%. These are packet/record counts, NOT direct classification as ACK-only. All eight Stop pass, CUBIC origin retransmits zero, mixed BBR total two; no shared TUN full drops. Capacity constrained by fq600, no uncapped or weak-network conclusion.

CUBIC middle SOURCE dual-ISA Normal functional run45815349281 PASS (real app bytes/hash/8 concurrent/UDP/half-close/Stop); fixture kernel OS CC still BBR, so not full all-CUBIC ARM test. Automatic x86 functional job independently rebuilt candidate; avoid duplicate build for subsequent same SOURCE measurements by retaining bundle where possible.

Decision: clean CC mismatch does not explain client CPU gap. No permanent CUBIC selection; keep exact CUBIC trial SOURCE available, restore intended BBRv3 when implementing next substantive reverse-path improvement (avoid standalone revert/test). Focus on actual ACK-only counts and segment sizes separately at local and middle legs, then reduce real packet/wake work with correctness intact; high-RTT/loss and ARM performance follow. Default Rust1.85.1 remains; old splice not retired. No product main merge. Main H2459 governance PASS; branch inherited historical cursor failure not rewritten.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Record matched CUBIC diagnostic and scoped dual-ISA CUBIC-middle functionality; no controller promotion."}
```
