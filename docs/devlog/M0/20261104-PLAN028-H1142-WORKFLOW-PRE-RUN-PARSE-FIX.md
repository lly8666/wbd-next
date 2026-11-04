# PLAN028 H1142 — fix H1141 workflow parse before native test

H1141 automatic [Action41828187039](https://github.com/lly8666/wbd-next/actions/runs/41828187039) failed during workflow parsing, with **zero jobs**: the generated YAML accidentally joined the last `apt-get install` line and following native step and retained a stray artifact filename fragment. This was entirely before the runner, original Go/Rust and any kernel packet path. Do not label it product FAIL or mark proposed independent outer-MTU test complete.

H1142 repairs only the two exact malformed YAML spans and the H1141 output marker, keeping one SOURCE-ab472 x86/x86 three-device scenario, original artifact13317049005 hash verified, D outer intent1280 against A/B default1460, server global TUN unchanged, real 70 UDP and all Rust Stop. Existing H1139 ARM64 PASS remains unaffected. No new product or duplicate test.

```feature-impact
{"kind":"none","ids":[],"reason":"Repair one invalid native workflow step boundary before any job ran; no application behavior or feature changed."}
```
