# Native M4 clock result and narrow ARM parity intent

392ee066c8bbcea96c20dea0ef76d73f497f6b87 run45930085832 both ISA product build PASS, 344 core + exact copied-prefix unit 1/1 each, original/parity Normal native app duplex hashes, eight concurrent TCP, half-close, UDP and owned Stop PASS. Original job logs and ZIP15167837607 x86 /15168156822 ARM inspected. M4 parity local receipts client/server copied 3214/9576 x86 and 3217/9652 ARM, all not_proven_copied/no_normal_pn zero; ingress full zero. This is a small functional workload, not throughput or loss qualification.

No ARM parity run existed for 392ee06: parity push paths only matched its own workflow and fixture. Narrow next candidate to one BBR zero-injected-loss 400ms, one stream, 45s ABBA against exact 26b11e2 Linux splice, existing three distinct ARM runners and cap64/ACK2. Add existing parity workflow/fixture paths to native workflow so deliberate parity changes produce exact same-source bundle; automatic push only, no dispatch. Preserve bare precheck and report capacity, path and local drops. This is a comparator for overall current parity, not a causal M4-only intervention. No product code change from 392ee06. New SOURCE unverified until exact run; old failed/limited evidence retained.

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Archive reviewed M4 clock native receipts and request one source-locked BBR zero-loss comparison; no product or default change."}
```
