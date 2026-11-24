# H2361 — isolate pure outbound checksum CPU work before WAN qualification

Independent branch experiment/m0-029-checksum-wide, exact H2336 product base bc87909 except outbound platform/ipv4_tcp.rs. Existing Internet checksum sum uses 2-byte loop. Eight-byte read yields two u32 terms congruent to original 16-bit sum modulo 65535; final original carry-fold/checksum unchanged, same odd-byte tail and <=65535 packet bound. No unsafe, allocation, new driver/offload assumption, RX validation change or protocol change. Existing byte oracle and golden packet tests, all 0..2048 lengths at 8 alignments and 65535 bounds/zeros/ones. Explicit ignored release microbench compares old exact scalar against new on identical 64 buffers, same process, alternating ABBA/BAAB order, seven sizes and six measurements each, prints actual medians/dispersion; Windows x64 and native Linux ARM independent jobs. No hardcoded performance acceptance or fabricated throughput. Only if local CPU evidence warrants it do a real WAN path comparison; no extra full true network trial yet.

```feature-impact
{"kind":"none","ids":[],"reason":"Equivalent outbound Internet checksum arithmetic, same wire bytes/driver ownership and feature behavior."}
```
