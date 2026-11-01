# H760–H761 GameFEC-only: parallel bounded rescue + honest pre-ready cold milestones

User-paused all unrelated PLAN027 tasks, task PARTIAL. Physical NOT_RUN.

H755 real signed original Windows Go TLS/Rust NPF/Wintun ↔ WSL2 Linux Game2/FEC6 1Mbps each, 25ms, 0% injection, 10s native run41291160670 source `0264c2cfc91e05c7c4b8d518fa0efc6707a2ff6b`, prebuilt build41280564979, final CANCELLED by watcher41291170270 at native ~484s. Target native job BlobNotFound. Independent stages PRE_NATIVE_STEP41291346357, STEP_ENTER41291350897, STEP_PREFLIGHT_COMPLETE41291376841, CLIENT_LOG_STARTED41291380242, SERVER_LOG_STARTED41291382191 **PASS as stage-only**. Authenticated TLS Ready, Rust TX/RX first error, real UDP/TCP and owned Stop **UNKNOWN**.

H759 Windows fixture41292885288 **FAIL**: slow serial relay emitted CLIENT_TLS_JOINED and CLIENT_OS_APPLIED but didn't emit OS_APPLIED before short fixture deadline. No product qualification. H760 product-independent harness change source f515c028, test source 031cf60d:
- Existing GameFecRelay's GH `workflow_dispatch` now uses bounded 3 concurrent daemon senders with 8s subprocess deadlines rather than serial synchronous calls that starve every later marker/first fault. No GitHub or log IO in owning PID loop; 100ms observer scan. GitHub outage can still lose evidence, no success inferred.
- One original E2E GameFEC-only append-only fixed enum `gamefec-cold-stage.txt` records E2E start, WSL real IP, TLS cert, Windows client spawn, before real Go/Rust client/server READY, actual READY complete. All stages require actual progressed process lines. No TLS secrets/keys/passwords, no simulated handshake or packet.
- One Windows-only synthetic [41294043519](https://github.com/lly8666/wbd-next/actions/runs/41294043519) **SUCCESS**: six relay tests including slow GitHub CLI, appending stages/no-leaks; Python syntax. Source f515 main governance [41294003261](https://github.com/lly8666/wbd-next/actions/runs/41294003261), source031 main governance41294043535 and maintenance41294043512 **SUCCESS**.

H761 controller `.github/workflows/m0-plan027-h761-gamefec-cold-stage-single-original.yml` verifies those exact prior green tests, Git frozen signed windows/Linux same-source binary artifact build41280564979, unchanged product crates/Go overlays, exact 1M/25ms/0%/10s Game2FEC scenario, existing 250s PID deadline and 480s independent native-step limit. One real original run only, no Mode/Auto/Fixed matrix; controller green is not product PASS. Next collect stage receipts `COLD_WSL_IP_READY`, `COLD_TLS_CERT_READY`, `COLD_CLIENT_SPAWNED`, `COLD_READY_WAIT`, `CLIENT_TLS_JOINED`, `OS_APPLIED`, `COLD_READY_COMPLETE` and actual first failure or owned Stop. Existing H755 timeout/BlobNotFound stays negative.

```feature-impact
{"kind":"none","ids":[],"reason":"GameFEC fixture and independent cold-stage evidence path only; original Go/Rust product binaries frozen. No real GameFEC delivery/Stop qualification before native result."}
```
