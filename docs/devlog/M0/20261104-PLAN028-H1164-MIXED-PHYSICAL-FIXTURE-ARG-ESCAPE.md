# PLAN028 H1164 — one-character generated Bash optional delay fix

H1162 ARM mixed-mode physical original Go TLS/Rust scenario was queued but not running when source review caught a generated shell bug: the test-only Python generator's string used `\${6:-0}` instead of `${6:-0}`. This would suppress Bash optional sixth argument expansion and feed a literal `${6:-0}` to Python `float()`, failing at the first 5-argument UDP send before any authenticated physical switch. Correct exactly one character in `tools/m0-plan028-arm64-mixed-game4-physical-fixture.py`; the original native products, TLS/route-key, Rust M4/FEC, default outer1460 and steady wire are untouched. Prior queued H1162 Action41863838024 is not classified as product failure and its actual result must be collected. The corrected workflow reuses the exact H1162 single scene; no new old matrix or helper dispatch.

H1163 separate signed Windows original Normal current-source Action41864386204 is in queue; Windows does not count in Linux ARM/x86 alternation. H998 historical same-connection hot-MTU shrink remains FAIL, Android/physical Wi-Fi/remote ICMP/CPU causal not proven.

```feature-impact
{"kind":"none","ids":[],"reason":"Single-char shell expansion correction in test-only ephemeral generator; no runtime change."}
```
