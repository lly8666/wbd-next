> **已被中央 v2 范围审计替代（SUPERSEDED，非未解决请求）。** 按最新 `main/docs/GOVERNANCE.md` §10，旧 worker G2 工具的累计64次上限不再阻止 PACK-013 交接。中央精确源码 [39006312629](https://github.com/lly8666/wbd-next/actions/runs/39006312629) 与先前完整 HEAD [39006679848](https://github.com/lly8666/wbd-next/actions/runs/39006679848) 均 `ROLE_SCOPE_PASS`，实际 ZIP 和 JSON SHA256 已独立核验。**不再要求 M0 复制检查器、批准工具例外或重跑旧失败。** 本文件后续内容仅为历史故障与当时请求记录；原有失败仍保留。此次修订属于 task013 交接证据 S，不能用旧 HEAD 的 PASS 代替此后新 HEAD 的独立中央范围检查。

---

# M4 → M0: frozen G2 checker bound stops task 013 (real blocker)

**Status: BLOCKED_NEEDS_M0_G2_REVIEW.** Role M4 / `R1-M4-LEASED-KERNEL-MULTIMSG-WORKPACK-013`; registry revision2, epoch1, branch `work/m4-r1-platform`. Final code SOURCE `b7bcde7dde64633532cae99460eb00855a2e119a`. No root/Cargo/engine/ABI/main path modified by M4.

Native same-code GitHub Actions run [39006105820](https://github.com/lly8666/wbd-next/actions/runs/39006105820) compiled once Linux GNU Rust1.85.1: **94/94 R1 PASS**; real build and result ZIP SHA independently verified. Code Governance [39006105815](https://github.com/lly8666/wbd-next/actions/runs/39006105815) attempts **1 & 2 FAIL** exact `ROLE_SCOPE_FAILED: incomplete or diverged bounded G2 activation ancestry`, not a test regression.

**Reproduction:** frozen worker branch `tools/worker_scope_ci.py` checks `0 <= total <= 64` and complete compare list for `83bd720368b9be68b3c4c94d7462d20cf4d796db`→`b7bcde7dde64633532cae99460eb00855a2e119a`. Live GitHub compare yields `status=ahead`, `behind_by=0`, `total_commits=ahead_by=66`, 66 returned exact commits and last = frozen SOURCE. The reviewed main checker supports 512 commits with complete pagination, but **tools/** is outside M4's allowed_paths. Repeating the identical branch checker cannot pass; adding cursor/evidence raises count further. The history should be fully audited, not truncated to 64.

**One action requested from M0:** under M0 exclusive root/checker authority, review and authorize an exact-parent, one-time G2 checker synchronization or equivalent M0-controlled bounded validation of all worker commits, with any necessary narrow scope exception. Do not grant general M4 root/tools write. Preserve all authored commits and failed runs. Once verified, M4 can rerun same SOURCE Governance, validate evidence and finalize cursor-only H; until then task **not ready_for_integration**.

**Not claimed:** Privileged raw IPv4/AF_PACKET positive, configured TUN positive, real physical route/link churn, authenticated Go V4 TLS→Rust AEAD/PN owner, Windows/ARM native, 500Mbps/p99 are **NOT_RUN**; production Go V4 DISABLED. Old R0 workflow fails historic test count although 102/102 Rust assertions passed; see evidence.

This Markdown is a control-plane escalation, **not** a functional/performance/governance workflow-dispatch request; it must not be mistaken for a `validate_request` JSON action. Initial JSON escalation path `.governance/workstreams/M4/requests/R1-M4-LEASED-KERNEL-MULTIMSG-WORKPACK-013-G2-64-LIMIT.json` was written in previous S, then replaced by this human-readable request to avoid colliding with the Actions request schema.
