# M0 / 024 · Same-VM Rust hot-path paired P10 CPU / delivery evidence (2026-10-17)

## Trigger for this patch

Main H112 `60ea1c5f11598cbfd24505b47c8b09b62f935d5d` already had protected Go→Rust native Linux real raw/TUN success for DATA return budget64 but **no valid CPU comparison**. M3 scope failure at worker `c900f7a4` has already been corrected **by M3 itself**, with H `d9ed1ad3`, central [39003896454](https://github.com/lly8666/wbd-next/actions/runs/39003896454) SUCCESS and worker Governance [39003788619](https://github.com/lly8666/wbd-next/actions/runs/39003788619) SUCCESS; old FAIL [39003738130](https://github.com/lly8666/wbd-next/actions/runs/39003738130) retained. No reason to bypass scope checker or edit the M3 active branch.

M0 repaired **both** obsolete P10 workflows in S `51bc18df7eae51c219210c9dca48262ce56db40b`, pinning A to frozen `a3d64b10804e006fecf06b7b4eb2d974b0b54e57` and B to same tracked Rust implementation as `b8d53e794dcf641a965e785c7c0aad03ad45ae37`. The SOURCE at the workflow-only main commit is B, and its `v4_embedded_go.rs` git blob must match `4ea790403b89190bd3a6eaf587aff836de0be173`; A must match `23f675d6426190a1a98ca3454cfa234e5359525a`; original crypto owner git blob identical `3287bf49437023bce867314af43423234ce3a5f9`. Identical Cargo.lock, Go test fixture and owned netns script checked before building. Build once A+B, artifact verify in independent consumer; each consumer measures **same job/same VM**, non-overlapping A then B or B then A, not cross-VM absolute CPU subtraction.

## Results — true original authenticated Go/Rust path

| Scenario | Run / SOURCE | A normalized CPU-s/GiB | B normalized CPU-s/GiB | B minus A percent | Delivery / integrity | Same-host p99 age C2S/S2C, A→B |
|---|---|---:|---:|---:|---|---|
| P10-AB | [39005769143](https://github.com/lly8666/wbd-next/actions/runs/39005769143), `51bc18df` | 151.662474 | 151.446260 | −0.142563% | each leg bilateral ~10Mbps, missing 0 invalid 0 | A 161/169µs; B 161/169µs |
| P10-BA | [39005769170](https://github.com/lly8666/wbd-next/actions/runs/39005769170), same `51bc18df` | 152.120314 | 151.156163 | +0.637851% | each leg bilateral ~10Mbps, missing 0 invalid 0 | B 171/172µs; A 173/184µs |

Both workflows **build+measure SUCCESS**, SOURCE/harness/flags/hash verified, 10s warmup + 60s measurement and single-job sequential leg ordering. AB artifact result ID `12091221974`, digest `sha256:a28a63108cd4df4917f5a9bd6ace93d4f5301d17e8bd2d947a6ea84ecbddbee9`; BA artifact result ID `12090544321`, digest `sha256:44ed0ab26557e2f27c4e52ae69b79b16da357e0a340bb37a4d30a0eccb0788f7`. Full build artifact IDs and per-leg raw hash, CPU/process/user+system, p99, delivered bytes captured in [evidence](../../evidence/M0/M0-024-P10-sameVM-AB-BA-return-budget64.json).

**Interpretation:** CPU sign reverses and both paired shifts are below ±1%; return budget64 is a correct bounded fairness safeguard, **no measurable/reproducible CPU saving** in this 10Mbps workload. Do not average CPUs across GitHub VM instances or advertise product 500Mbps, Rust CPU reduced, or old Go-vs-new Rust gain. Same-host p99 is not WAN RTT or product SLA; no repeated latency regression here. Physical, product and original R0-M0-023 remain NOT_RUN/OPEN_UNVERIFIED, production features0. Same-session TX/RX mutation still serialized behind `Mutex<Entry>`, real raw kernel sendmmsg waiting M4-013, new SPSC wake/STOP waiting M1-012.

## Next batch

Respect 024 spec section6 bounded diagnostic set: independent **SPARSE-AB** 20pps and **D10-AB** diagnostic ON, each same source and original Go authentication/raw/TUN (never secretly run P10 twice with a different label). Avoid adding diagnostic syscalls to P10. C50 only when capacity justified; no 500Mbps inference. No further samples just to cherry-pick a positive sign.
