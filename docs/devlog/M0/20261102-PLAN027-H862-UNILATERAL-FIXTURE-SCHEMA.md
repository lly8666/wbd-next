# PLAN027 H862 | Recover unilateral scenario fixture before native measurements

- H861 unilateral [Action41378640770](https://github.com/lly8666/wbd-next/actions/runs/41378640770) **failed pre-native**: `LinuxExperiment` returned `KeyError: 'jitter_ms'`, no observed rows, no actual kernel loss or business; its artifact result FAIL is strictly malformed phase descriptor (new unilateral helper rebuilt `cfg["phases"]` with only delay/loss/rate). It is not a product rejoin failure and no data justify a product change. Independent source same H859/H860 original Go TLS/Rust M4 once bundle Action41378386073 PASS and manifests three exact hashes. Bilateral H861 Action41378640754 is independent and not canceled/repeated.
- Fix only test scenario: use already validated full `m0_plan027_linux_blackhole_recover.configuration` phase structures with original jitter_ms and all kernel fields, rename `double_blackhole105` to `c2s_blackhole105` and set **only s2c loss 100→0** in that phase. All real original source TCP/TUN/Health, ON/OFF default, 20s/105s/120s/2Mbps/25ms no probes unchanged. Unit asserts preserved `jitter_ms` each direction. Run exactly one corrected unilateral Action using original frozen bundle and source hash, do not rebuild any product.
- No Windows physical or 10Mbps recovery scope promotion, no arbitrary data plane tuning.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct one missing netem fixture field by deriving asymmetric loss from validated phase config; no product code or public option."}
```
