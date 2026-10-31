# PLAN027 H589 — one current SOURCE original-Go A5 retest, safe substage oracle

Old source525 Windows/WSL2 A5 Action41167365369 established same-VM RustB first/Stop PASS, but original Go steady A exited after 50.812s. Report `a5_go_failure_stage=RUST_PEER` only and no owned Stop, no A/B CPU validity. The failure marker itself was hashed, not copied, so its product error subclass could not be recovered. Code has many distinct possible sources: a genuine M2 firstsend completion failure, feedback draft or completion, repaired source submission, original M3 seal/open, carrier sequence mismatch, finite retry, driver/ingress/lifecycle. Inferring a particular one from a generic wrapper is speculation.

H589 adds a *fixed allowlist* of product error substrings, stored only as an enum `a5_go_rust_peer_substage` alongside the existing SHA and stage. No raw error strings, packet, keys, PN, route, remote tuple, secret, or stdout are added to the uploaded report. One same-VM two-leg B→A true Windows/WSL2 signed origin test uses new current SOURCE `cb475c89` already frozen in successful build Action41177831521 and 10Mbps each,25ms,0%,60s. Does not rerun Game10, H584 loss series, or recompile product. If A fails preserve exact category and Stop evidence; if both pass report same-VM whole-process CPU/RSS, not speedup from cross-VM old data.

```feature-impact
{"kind":"none","ids":[],"reason":"Only allowlisted A5 harness failure substage and one true source-frozen same-VM original Go A vs native Rust B test. Product untouched."}
```
