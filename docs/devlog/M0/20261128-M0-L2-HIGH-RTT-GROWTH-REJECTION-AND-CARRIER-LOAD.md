# H2528 — reject high-RTT growth removal; isolate carrier load

Native run 46107055174 passed both ISAs, but exact db76055→dbb70af local weak ABBA fell from 60.25 to 22.33 Mbps; three-runner zero-injected-loss ABBA (46107055465) fell from 276.34 to 175.93 Mbps. All application hashes and EOF passed. Weighted local retransmission was 0.5384%→0.5298%; retired cross-host retransmission 1.5362%→1.4053%. The lower attained receiver buffers and higher unit CPU costs do not justify removing the extrapolation. The active receive buffer grows monotonically; the measurements do not prove active shrinking.

Re-read the eight capture artifacts by WBD product tuple, excluding bare TCP port 5202 where GRO aggregates change the header identity. Four product cases in ABBA order have server→relay sampled missing identities [26,2,100,28] and relay→client [120,158,140,219]; other adjacent gaps and all extras are zero. All eight captures report zero kernel capture drops. The previously combined bare/product comparison was confounded by GRO. This locates the observed sampled deficits between runners, not a measured physical loss rate.

Restore autotune.rs byte-for-byte from db76055. The new runtime is not another tuning candidate; retain the original dynamic growth, low RTT behavior and existing flow control. Qualify the restored SOURCE through both native ISAs and the existing local clean/pause/weak check.

Next: fixed exact db76055 ARM64 binary (run 46102235913), 1GiB application, 400ms added RTT, zero injected loss, Normal/repair/MTU1160 unchanged, same three hosts, ABBA offered application loads A=120M/B=600M. Both manifests and all three product binaries must match; the old qualified artifact is downloaded once per endpoint and reused. Bare 600M brackets remain. Compare observed delivery, CPU, retired retransmission and product-port-only path identities normalized by sampled TX counts; no product pacing/window cap, no change to carrier or protocol. This is an offered-load diagnostic, not an architecture performance qualification. No result yet.

Evidence: docs/evidence/M0/20261128-L2-HIGH-RTT-MEASURED-GROWTH-RESULT.json

```feature-impact
{"kind":"updated","ids":["dual-rust-tcp"],"reason":"Record negative high-RTT candidate, restore exact selected runtime and isolate carrier load using existing qualified binary."}
```
