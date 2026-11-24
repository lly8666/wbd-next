# H2364 — retain proven checksum work; drop inconclusive arena increment

M0 resumed H2363 and read all five completed Actions. Exact source and actual receiver log legs; no main product change. H2347 settlement (45321088128) B vs A mean -10.9%/-5.0%; reject. H2349 arena (45321102114) +5.5%/-13.2%; remove three Rust trial deltas from active branch by restoring exact H2336 bc87909 blobs. H2358 local reclaim (45321120476) +6.9%/+0.3%, group b P99 610ms in B vs 281/391 A, do not combine. H2359 application supply (45321409323) -7.9%/-6.4%, group b bare 1184.901 Mbps and product A' 391.458 Mbps; no fixed 150 Mbps ceiling, but supply increase alone not a win.

H2361 (45321513988, 17ade976): Windows x64 and ARM64 checksum tests 22/22 each; release median 1460B 275.031→141.515 ns and 190.799→82.917 ns. Adopt the exact tested wide arithmetic in the experimental product branch. No new mechanism or runtime setting. H2364 freezes one Rust-file difference from H2336; reuse existing source-isolated calibrated crossover workflow, same signed native product, no repeated standalone microbench. Performance qualification pending; no main merge or default change. Continue with service-path bottleneck rather than blind queue/buffer scans; advance P1 then P2 without requiring an unachievable physical target to start functional work.

```feature-impact
{"kind":"none","ids":[],"reason":"Restore previously retained H2336 runtime and adopt equivalent outbound checksum arithmetic; no product capability, settings, or wire behavior changed."}
```
