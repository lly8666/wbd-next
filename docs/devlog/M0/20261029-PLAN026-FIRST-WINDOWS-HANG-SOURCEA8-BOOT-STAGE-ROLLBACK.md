# M0 PLAN026 — historical Windows hang onset found / split true WSL boot from native product

2026-10-29, source-only CI fixture correction, main-only. This devlog intentionally does not assert an unobserved real Game product result.

## Exact version-ordered evidence

1. SOURCE 4c6a7c0 [Action 40847146468](https://github.com/lly8666/wbd-next/actions/runs/40847146468), 09:07–09:19Z, **completed FAILURE** with upload and owned cleanup; true signed Win+WSL original Go TLS Normal/Fixed/Auto each duplex+Stop PASS, Game2/4 worker rc3 NPF RX EndOfStream; source-specific.
2. SOURCE adc586c [Action 40848387586](https://github.com/lly8666/wbd-next/actions/runs/40848387586), 09:16–09:27Z, **completed FAILURE**, artifact; Normal/Fixed/Auto PASS, Game2/4 and fixed Game worker TX rc3 after pre-joined native capture, concrete product failure but no Action hang.
3. First independently observed stuck source: **a8df98e** [Action40859233957](https://github.com/lly8666/wbd-next/actions/runs/40859233957), started 10:39Z, ultimately cancelled 11:19Z; 134914f Action40860233126, a13bbdd Action40874802357 also hung/cancelled; a3605d Action40883632233 and current dc3323 Action40887375126 have native-public-two-os step14 in progress, API logs 404; do not infer they reached product Game2.
4. Source compare **adc586c..a8df98e** precisely changes `tools/m0_wl_public_modes_e2e.py` from the last terminating direct `subprocess.run(...)` to `subprocess.Popen(..., creationflags=CREATE_NEW_PROCESS_GROUP)`, each-mode .wait(timeout=165) and taskkill; Rust Game change only adds typed stages for first driver/owner error. Thus process launch/control is a temporally earliest suspicious regression, **not uniquely proved** root cause of WSL preflight hang.
5. Independently [real WSL2 parity Action40872857108](https://github.com/lly8666/wbd-next/actions/runs/40872857108) SOURCE6523 proves both old direct and new wrapped Windows-2025 official Ubuntu WSL2 boots genuine kernel/TUN (45s vs29s). So Windows host blanket WSL2 unavailability is disproven for that scoped parity, not blanket native product qualification.

## Minimal mitigation and discriminating next test

- For current full signed two-OS job, **cut original real WSL2 distro list/import, official digest, boot and kernel/TUN probe into its own bounded `shell: pwsh` step** immediately before native full. Preserve same VM, native signed Wintun/Npcap/HyperV/guest route and original Go/Rust binaries; don't mock any guest. Append exact-source precondition marker. A separate artifact upload happens even if following product stage wedges: the last successfully completed phase can now be inspected through GitHub job records and its genuine guest probe.
- Restore last known terminating Windows child launch semantics in `m0_wl_public_modes_e2e.py`: `creationflags=0`, removing the first-hang-era new process-group flag. Preserve per-mode 165s native deadline, actual rc, bounded taskkill for timeouts, file-backed PID stdout, 320s Game2 batch cap, and actual typed first product error. This is a deliberately controlled one-variable launch rollback, **not claimed fixed until new SOURCE real Action**.
- Python regression checks both workflow phase separation and single original-code launcher behavior; all product Go/Rust code & assembly manifest remain identical to frozen Game cold stop-aware Go product fix source6041a2.
- Cheap source contract → one new-source **Game2-only** signed Linux↔Windows native first/reverse UDP/TCP plus owned Stop. The current source dc3323 old separate true job is still useful once it ends; if stuck, mark UNKNOWN and require newly staged real boot proof. On real Game2 PASS target Game4 and then Auto original M2/Health idle/dead/FIN, same VM CPU A/B/physical later. Historic Normal/off N0/150M and Linux true Auto grade-down/Stop remain scoped accepted, don't replay old Normal/FEC matrix.

```feature-impact
{"kind":"none","reason":"Only GitHub Actions WSL2 real guest boot stage visibility, subprocess launch rollback, tests and M0 devlog; signed native Go/Rust product, FEC/Health behavior, user defaults and feature cards unmodified."}
```
