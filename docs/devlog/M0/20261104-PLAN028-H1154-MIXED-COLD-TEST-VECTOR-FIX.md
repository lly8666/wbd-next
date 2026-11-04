# PLAN028 H1154 — correct mixed-mode protected Go test vector, no product change

[H1153 Action41847734525](https://github.com/lly8666/wbd-next/actions/runs/41847734525) compiled the entire actual original x86 Go/TLS and Rust product. Before the native stage, `TestPLAN028MixedOne443OriginalProtectedNormalGame2Game4ColdPolicy` failed on Game2 with client `ErrAdmissionUnsupported` and the server bootstrap deadline. The test-only `v4PairFeatureProbe` had set byte22 `NormalFec=2` whenever `policy.FECMode==FECFixed` without also checking `TransportNormal`; Game2 and Game4 legitimately use fixed V3 FEC policy but must never carry a Normal fixed-strength byte. Original client correctly rejected this invalid mixed profile. Nothing from H1153 can be promoted as native mixed PASS.

H1154 changes only that test helper condition to `TransportNormal && FECFixed`, keeps fixed Normal strength tests and Game byte21 separate, pins `admission_v4_test.go` in the existing assembly manifest, and adds this one test source to the previously new workflow's triggers. No product wire, Rust, Stop, per-client identity or transport logic changed; one native x86/x86 Game2+Game4FEC6+NormalAuto real one443 UDP scenario remains pending.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"Correct one invalid mixed transport Go TLS test vector before the first real native x86 shared-mode scene; actual product unchanged."}
```
