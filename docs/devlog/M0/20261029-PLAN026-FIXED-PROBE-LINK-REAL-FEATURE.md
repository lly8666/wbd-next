# M0 H353 original Fixed kernel smoke Rust/Go feature consistency

Source e16f0436 Action40823894056 failed at original Linux Go CGO link: undefined references to wbd_m0_embedded_go_fec2_probe_live_peer_attach_tun and wbd_m0_embedded_go_fec2_probe_live_peer_consume. Both functions exist in original wbd-engine v4_embedded_go.rs and are explicitly gated by BOTH m0_fec2_owner_probe and fec2_product_record. The Fixed smoke workflow was compiling feature set m0_v4_probe,m0_v4_embedded_go,m0_fec2_owner_probe only, yet attempting to link its original-Go feature7 FEC probe. Enable fec2_product_record for that exact Rust smoke library and its declared feature manifest, not a stub or a lowered Go test. Default no-feature Rust build remains unmodified. This fix does NOT claim any real kernel/FEC2 product pass.

```feature-impact
{"kind":"none","ids":[],"reason":"CI feature-set consistency: the real Rust FEC2 probe exports already require feature7; add that compile flag instead of forging symbols or suppressing tests."}
```
