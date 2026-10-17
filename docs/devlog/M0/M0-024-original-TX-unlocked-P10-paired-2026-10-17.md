# M0 / 024 — Original TX syscall outside same-session owner mutex; paired P10 evaluation

The frozen M1-012 component had already been merged at S `acd184a1` and evidenced via H118 `42744982e28d03dbe6cbcbd0daa395a5ceda5d80`, [Governance39019057886](https://github.com/lly8666/wbd-next/actions/runs/39019057886) SUCCESS; M1 original H15 `9d4f68aa` remains READY scope but production feature **off**. We resumed from remote H118, not from an uncommitted assistant assumption. Other worker tasks M2-009 ready module, M3-016 partial, M4-013 ready module unchanged.

M0-only code S `8d41c6ff8b047d78332f2a8ab8951e49a8b2ec12` modifies only `crates/wbd-engine/src/v4_embedded_go.rs`. Previously TX sealed and synchronously wrote raw `sendmmsg` under the **same session Entry mutex** used by RX original AEAD/PN. Now M0 prepares and validates the real original M1 `LoanBatch<TxDispatch>` under mutex (Go-authorized route, original seal/PN/seq and live owner check), retains the same generation-held batch and immutable FrozenRecord outside the mutex during the true kernel `send_kernel_multimsg` call through Arc<ScopedRawIpv4Tx>, recycles exactly once, and reacquires mutex for route error revocation/return-budget64. Stop marks phase/shutdown and joins both workers before owner, M1 arena and M4 driver retirement; no separate ciphertext copy/nonce/alternate authentication. There remains a shared mutable owner lock for crypto TX/RX; this is **shorter lock critical section**, not yet true direction-owned independent mutable owner.

Same-source Go TLS→Rust original AEAD/PN→M4 Linux raw/TUN [native39020336918](https://github.com/lly8666/wbd-next/actions/runs/39020336918) full **SUCCESS**, G2, native regression, ABI, Qualification and Governance source-same SUCCESS. Actual kernel loss of PN0 / PN1 application delivery, MTU65536→1500 fail-close, netlink revision1→2 and bilateral ~10Mbps 10s+60s developer Normal/off all succeed. Artifact IDs/digests preserved in [evidence](../../evidence/M0/M0-024-original-TX-unlocked-P10-paired-e26e5d52dbebb17f9a60a9f8fc5ccc2c9093f963.json).

## Actual paired P10 result

Exact baseline A `42744982e28d03dbe6cbcbd0daa395a5ceda5d80` vs B implementation `8d41c6ff8b047d78332f2a8ab8951e49a8b2ec12`; compare A...B proves **only** `v4_embedded_go.rs` differs. Main CI workflow-only snapshots `cd2dd78b` for A→B and `e26e5d52dbebb17f9a60a9f8fc5ccc2c9093f963` for B→A check the same A and B engine git blobs, Cargo.lock, Go traffic generator and Linux netns runner. Each workflow builds two binary alternatives on one runner, consumes immutable SHA/digest-checked artifacts in one independent job/VM and runs two nonoverlapping 10s warmup + 60s windows at ~10Mbps each direction, 64/256/1200B mixed. None lost or invalid.

| Paired order | Workflow | A CPU-s/GiB | B CPU-s/GiB | B vs A | Same-run delivery |
|---|---|---:|---:|---:|---|
| A→B | [39020675956](https://github.com/lly8666/wbd-next/actions/runs/39020675956) | 156.493785 | 157.983808 | **+0.952%** | both legs bilateral ~10Mbps, zero loss/invalid |
| B→A | [39020694554](https://github.com/lly8666/wbd-next/actions/runs/39020694554) | 113.846948 | 111.275395 | **−2.259%** | both legs bilateral ~10Mbps, zero loss/invalid |

**Strict interpretation:** CPU direction reverses and separate VMs vary materially, **CPU benefit INCONCLUSIVE**. No cross-run absolute CPU subtraction, no 500Mbps, no throughput gain claim. Functional and original secured owner path pass only. The previously successful SPARSE20pps and failed D10 full ptrace evidence remain unchanged. Remaining loom dev-only wake Stop, full M1 session TX/RX direction-owned mutable path, actual M4 <=32 ready live batching, native M3 FEC-on, product/physical and old R0-023 all open. Keep prod features0.

S must add independent SOURCE-named evidence without overwriting H118 reference; next H cursor-only switch after successful S and governance, exact SOURCE guard unchanged.
