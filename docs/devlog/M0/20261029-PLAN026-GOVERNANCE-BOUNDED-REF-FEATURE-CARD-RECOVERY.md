# M0 PLAN026 — governance context references and feature-card size recovery

2026-10-29, **only provenance normalization**, not Game2 product behavior.

Signed SOURCE768b1e0 ACK-only actual native repair and frozen [real Windows↔WSL2 Game2 Action 40896052535](https://github.com/lly8666/wbd-next/actions/runs/40896052535) remain immutable and in progress until source-locked native result. That commit's governance Action40896052604 FAIL was independent of Rust code: role step reported `SCOPE_AUDIT_FAILED: unbounded context_refs` (H368 had 13, now exact 8); feature catalog reported `feature card must be bounded regular JSON` because **previously present** `windows-native-transport.json` was 16,735 bytes, above hard 16 KiB limit. Remove only three verbose duplicate historical limitations already in the card's verification/doc evidence. Do not erase old PASS/FAIL entries, source hashes, original feature defaults, platform limitations or acceptance gates. Post-cleanup card is 15838 UTF8 bytes.

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"Trim duplicated historical explanatory limitations to keep existing Windows NativeOwner feature card inside governance 16 KiB bound; complete evidence/verification rows and original product source untouched."}
```
