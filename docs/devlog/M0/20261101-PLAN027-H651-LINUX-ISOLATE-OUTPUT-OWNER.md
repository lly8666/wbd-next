# PLAN027 H651 — isolated Linux fixture setup, no FEC verdict yet

H650 [Action41218976128](https://github.com/lly8666/wbd-next/actions/runs/41218976128) verified all immutable original-Go TLS/Rust SOURCE11f hashes and deterministic isolated Linux GameFEC fixture overlay. It failed **before actual first UDP/Stop**: `fixed-kernel-result/public-v4-normal-business.log: No such file or directory`, because the historical combined-build job created that output directory but the new frozen-artifact-only job did not. This is a harness initialization mistake; preserve H650 FAILURE and do not attribute it to Rust FEC/Windows NPF.

H651 creates only the missing owned output folder before invoking the **same original** Linux netns source-locked Game2/fixed6/15%/UDP/parity/Stop one-scenario action. Do not change cryptographic/source binaries, deadlines, outcomes or requirements. GameFEC Windows and B106 original cancellations remain blockers.

```feature-impact
{"kind":"none","ids":[],"reason":"Only creates test-owned native Linux output directory and corrects cursor; no product source or capability changes."}
```
