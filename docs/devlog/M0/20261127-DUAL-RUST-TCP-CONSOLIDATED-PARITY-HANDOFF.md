# M0 consolidated Linux TCP parity — handoff

[Result](../../evidence/M0/20261127-DUAL-RUST-TCP-PARITY-HOTPATH-RESULT.json) SOURCE 935a6317969486846fec60fe98f35d2429dfedcb: native dual ISA 339/339, scoped original/parity Normal PASS; hotpath ABBA 8/8, BBR -11.6% throughput / +6.3% two-end product CPU/GiB; CUBIC +24.7% / -14.7%; no candidate promotion or per-change attribution. User directs grouped basic behavioral alignment. SOURCE 65aae40cdbd99c0a9957518db1748ad533181bdc: [full comparison and remaining gaps](https://github.com/lly8666/wbd-next/blob/65aae40cdbd99c0a9957518db1748ad533181bdc/docs/devlog/M0/20261127-LINUX-TCP-PARITY-CONSOLIDATED-BEHAVIOR.md), native 45916282014 and ARM Linux/Rust ABBA 45916281816 in flight. Note BBR Ack.flight is prior unacked sequence bytes, not fully equivalent to Linux prior_in_flight pipe under SACK; still partial. Exact Ubuntu patch-set, receive fast path, actual owner timing/TSQ and TSO, extended AccECN and PMTU remain open; fixed WBD MTU retained. No duplicate dispatch. No main product merge. Governance prior structure failure remains.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Publish experimental branch's updated feature metadata and exact source evidence, without main product integration."}
```
