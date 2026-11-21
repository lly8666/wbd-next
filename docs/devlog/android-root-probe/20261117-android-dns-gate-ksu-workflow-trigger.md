# Source-locked KSU CI path coverage for DNS UDP gate

The Android KSU real-AVD workflow originally enumerated Rust modules by filename. Its `push.paths` omitted newly added `experiments/android-root-probe/probe/src/dns_udp_gate.rs`. As a result, SOURCE `10ef80cbf77f12fcc2b9d3affb6422a743d52013` automatically triggered a native Android build and governance, but **not** KSU execution; no KSU PASS may be attributed to that SOURCE.

Add the native DNS kernel gate module to the explicit KSU workflow path list. This ensures every subsequent change to DNS packet send/response assertions triggers the complete real Android16 KernelSU end-to-end App button → Root full geosite → six isolated kernel UDP/53 checks and original TUN/NAT/recovery regressions. No main Android route or product WBD code touched.

```feature-impact
{"kind":"none","ids":[],"reason":"Include new dns_udp_gate.rs in the original branch's source-locked KSU Android workflow push.paths; prevents silent absence of real DNS integration testing."}
```
