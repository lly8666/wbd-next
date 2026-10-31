# PLAN027 H653 — Fixed200 controller rejected legitimate B106 test oracle before native dispatch

[H652 dispatch Action41219400009](https://github.com/lly8666/wbd-next/actions/runs/41219400009) is FAIL **before** any Fixed200 Windows/Linux job was launched: after fetching original product SOURCE11f, its `git diff ...` guard incorrectly included `tools/m0_wl_public_normal_e2e.py`. An exact compare SOURCE11f→H652 found no diff under product Rust/Go, Cargo, assembly, netem or performance config paths, only six lines of H647 test-only bilateral original TLS reauthorization oracle. H649's otherwise-identical correctly source-locked gate omitted this file and delivered original Fixed100 and Fixed50/300 positive Actions.

H653 reuses proven H649 frozen-product guard and separately checks that test-only B106 oracle still requires the real Windows and Linux new TLS generation. Binary SOURCE and download SHA manifest requirements remain strict. No public Fixed200 PASS inferred and no new product implementation; one Fixed200 native Action only after gate passes. GameFEC Linux positive from Action41219083345 remains scoped; repeated Windows GameFEC/Normal B106 cancellations remain blockers.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct only test-only B106 oracle versus frozen product source-lock distinction in Fixed200 dispatch; no runtime/feature changes."}
```
