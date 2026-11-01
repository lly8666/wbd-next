# PLAN027 H840 | Exact 100Mbps fixture repair (pre-native only)
- H839 copied the healthy 50Mbps trial with an excessively broad literal replacement. It accidentally changed **historical base scenario filename 250ms→2100ms, pinned GitHub checkout digest, and frozen f5 product SHA**, plus theoretical pps/RTT. No product code changed, and this corrupted request must not count as a product performance result; any H839 Action preflight FAIL is strictly fixture-only.
- Restore exact base `scenarios/plan027-h539-normal-10m-250ms-loss0-60s.json`, exact checkout digest `11d5960a326750d5838078e36cf38b85af677262`, original frozen SOURCE `f5e8f30fa4a5052c9797bbd15b385ec5cfc5d2c3`, 100Mbps/1200B = 10,416.67 business PPS/direction, RTT50ms ⇒ BDP625,000B/direction. Keep one independent source-frozen original Normal OFF100/25ms zero-loss 60s task, no extra variants or false PASS.
- H837 true blackhole double 105s after native dead/cold TLS still FAIL client exit1, separate lifecycle problem. No product change, no recovery regression qualification here.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct test-only 100Mbps frozen source/checkout/scenario references and theory; product untouched."}
```
