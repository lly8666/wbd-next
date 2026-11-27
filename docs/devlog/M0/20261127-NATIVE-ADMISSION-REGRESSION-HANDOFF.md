# M0 native admission regression handoff

[Reviewed evidence](../../evidence/M0/20261127-DUAL-RUST-TCP-NATIVE-ADMISSION-RESULT.json). 586706c native PASS, ARM24/24 not qualified (BBR0 Linux261.17/Rust194.96 Mbps, CPU/GiB28.49/41.77).  ba5ed73 344/344 core each, real opt-in concurrent app reset on both ISA, performance gate blocked. x86 failure archive confirms no ingress loss, no local write error, pending peaks98/224. Actual reset origin not established. New SOURCE 9ede62e1aa3e2a1396c73d899f78e21db1db4920: [code record](https://github.com/lly8666/wbd-next/blob/9ede62e1aa3e2a1396c73d899f78e21db1db4920/docs/devlog/M0/20261127-NATIVE-ADMISSION-REGRESSION-AND-READY-BATCH.md), restore drain-before-service, retain outstanding grant; fix premature RTO/FIN, batch already ready TUN lock with actual attempt receipts, no new cross-flow FIFO/queue capacity or outer wire contract; no physical GSO or M4 timing parity. Run same-source native gate then 8-leg BBR0/CUBIC0 Linux ABBA. Latest run list in evidence as observed; refresh remotely, do not duplicate dispatch. Existing governance failures remain. No main product merge.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Publish experimental regression correction and reviewed evidence; no main product integration."}
```
