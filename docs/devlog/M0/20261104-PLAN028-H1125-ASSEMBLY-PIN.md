# PLAN028 H1125 — original Windows Go assembly pin correction

H1124 [Action 41809723276](https://github.com/lly8666/wbd-next/actions/runs/41809723276), [41809723348](https://github.com/lly8666/wbd-next/actions/runs/41809723348) and [41809723371](https://github.com/lly8666/wbd-next/actions/runs/41809723371) failed before original Windows native product assembly: manifest-plan020-m0.json result_blob was H1123 source 9e1e92ff66c1faa27343788b429ca92ae264bd29, whereas H1124 Go source blob is fe209c2094aa2a687ef85232d8d7818dfb92611e. This commit corrects the one exact existing manifest operation only, no Go/Rust code changed, original donor hashes unchanged. It re-enters one original signed Normal native Action via [plan028-win-physical-owned], not the old seven-mode matrix.

Status after this commit: H1123 original native product failed pre-TLS READY, H1124 pre-assembly failed; Windows original TLS/Npcap/Wintun new source4 and first business remain pending. H998 online same-connection hot-shrink FAIL, historical ARM64 Game4FEC Action FAIL, remote ICMP NOT_MEASURED, CPU causal gain unproven all remain.

```feature-impact
{"kind":"none","ids":[],"reason":"Exact assembly manifest source blob corrected with no product behavior change."}
```
