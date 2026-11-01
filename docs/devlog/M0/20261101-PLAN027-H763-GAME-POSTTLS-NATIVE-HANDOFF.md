# PLAN027 H763 — Game2FEC postTLS boundary and governance

User scope GameFEC ONLY, all other PLAN027 tasks paused. Task PARTIAL, physical NOT_RUN.

Original signed Windows NPF/Wintun Go TLS/Rust ↔ Linux WSL2 Game2/FEC6 1Mbps per direction, 25ms, 0% injected damage, 10s run [41294182175](https://github.com/lly8666/wbd-next/actions/runs/41294182175), SOURCE `0264c2cfc91e05c7c4b8d518fa0efc6707a2ff6b`, was **CANCELLED** by watcher [41294188947](https://github.com/lly8666/wbd-next/actions/runs/41294188947) at approximately 507 native-step seconds (configured 480s; check polling), job log BlobNotFound. Independent GitHub receipts **do** prove `CLIENT_TLS_JOINED`, `SERVER_READY`, Linux UDP alive and true TLS certificate creation and client spawn. Windows OS Applied, actual bidirectional first delivery, Rust TX/RX, Wintun/NPF handoff and owned Stop remain UNKNOWN. No product PASS; only guest-boot artifact13078446971 was available.

H762 SOURCE `dd42a5622a158c4b46a1ec9973a8cc08902fe607` adds 19 bounded diagnostic stage markers inside existing real Windows original Go Game cold path and Rust NPF handoff: Wintun open, plan prepare, product prepare, Wintun Rust bound, NPF reader join, capture moved, Game Rust start, WAL Apply, live receipt, cleanup join. The separate GameFecRelay enumerates only fixed markers, no packet/key/identity, and assembly manifest matches new Go blobs. This is **diagnostic-only product-source change** with no hot-pump or protocol alteration; old SOURCE0264 binaries do not contain it, so must NOT be reused.

H762 governance Feature catalog FAIL because product file change lacked a changed devlog feature-impact declaration; H763 fixes this without weakening the policy. H763 runs a targeted Windows Go original source assembly/build/test plus relay synthetic tests **without** WSL, Npcap, Wintun or a fresh product test. Only after green, one new same-SOURCE signed Windows/Linux 1Mbps Game2FEC native run under existing PID250s / watcher480s. No extra watchdog, no general PLAN027 mode dispatch.

```feature-impact
{"kind":"none","ids":[],"reason":"Diagnostic-only fixed enum stage markers around original Windows Go Game postTLS handoff/owner Apply and separate bounded relay; no product transport semantics or user-facing behavior changed, and real FEC remains NOT_RUN for this new source."}
```
