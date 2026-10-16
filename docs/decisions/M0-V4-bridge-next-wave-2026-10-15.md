# M0 formal next wave: protected V4 owner integration and bounded R1/R2/M3/M4 edges
Date 2026-10-15. Main source baseline dd9c4b1f66e40a4823c4153779931802409a3178. Authority registry rev2 epoch1 active; no worker branch, allowed_paths, owned_semantics, global-writer, role state or epochs changed. M2 priority fulfilled before new assignment. Main CODE integration from exact scoped sources:
- M2 pure R2 SOURCE ba7b45138cd416dcd3ce315c7111c9429829afdd, worker native 51/51, full 75 ancestry reviewed run38690653354 SUCCESS and final M2 H 014d636eaf0319ca3c0a456901b383d94b7214f1 Governance38692656343 SUCCESS. Main import a8e5a77afa4ee660de634aceca23025ce146fd8c, main R2 pure workflow38691506375 SUCCESS and R2 opened ingress38690933580 SUCCESS.
- M1 SOURCE 39e6dfc0e3d7dfec12af0c28849b36d8f82b23ed native 80/80, worker H5399ca Governance38689191231 SUCCESS. Main import002b388da763f9de185b9f7ad3f5040e278e36db; main scoped owner wake-stop38691375348 SUCCESS and R0 native ABI38691375310 SUCCESS.
- M4 SOURCE39f7671b07c3aa5f54266f42e83bc226a67c5763 native71/71, H44534bac Gov38689255498 SUCCESS. Main import2a1c5785b95d0b89963c62b133ee0f0099174f91, Linux RX/TX 71+6 native38691637699 SUCCESS, packet IPv4/TCP38691637693 SUCCESS, fake platform38691122549 SUCCESS.
- M3 SOURCE88a12027c61386be2709e1e8b01eb8f3c547ae81 debug98/98, H e411dccaf0c8f2a332ae1ce1f22457f5604b894c Governance38688674718 SUCCESS, main test source import a387d1bb801cdd99429b2836c03a0204b2f14b04. M0 Release38685587150 native 24/24 SUCCESS **but invalid CPU comparisons**: 22/24 thread_cpu_s > wall_s × 1.02, procfs sampled outside active timer, CPU clock 100Hz. All historic numbers are quarantined; main FEC/codec/record regression runs at a387 in progress or PASS as observed, do not invent finishing status.
- M0 Go protected V4 transaction was hardened: protected final write+Detach before explicit Go epoch finish(true), abort defer finish(false); actual protected TLS+rollback 11/11 source dd9c4b1f66e40a4823c4153779931802409a3178 run38695761347 SUCCESS. Still NO protected-Go-to-Rust installed owner/production ABI.

## Formal assigned tasks
2026-10-16 执行粒度更正：`docs/architecture/TEST_PLAN.md` 第 0 节是当前功能批次/持续业务/开发性能基线的统一入口。任务 ID、权限和下述正式 Exit 不变；Exit 不意味着每个参数逐项交接，也不阻止已可安全运行路径先取得明确限定的开发基线。完整资格与默认 capability 仍依真实证据开放。

施工顺序更正：M0 按 `docs/architecture/modules/01-CONTROL-BRIDGE.md` 的 Prepare→受保护回复→DetachTransition→CommitAdmission→双 owner 确认→Active 执行，废止早期“Active 后 Detach”描述；实际接入和 Normal/off 首到的分步交付见 `11-IMPLEMENTATION-GATES.md`。任务 ID、权限和 worker 分配不变，下面历史基线不代表最新进度。

### M0
R0-M0-V4-PROTECTED-OWNER-COMMIT-023: Main-only bridge that accepts an actual Go V4 authenticated protected ColdSnapshot exclusively through the trusted session/handshake callsite and installs one fresh Rust ScopedOwner generation with exact PrepareTransition/protected reply/DetachTransition/CommitAdmission transaction ordering, bounded early RX and TX seq ownership, fail-close on invalid/stale/overlap and Stop-held lease. A self-consistent 248B cold bundle is never authentication. Default production ABI remains features0 until actual E2E test and safety signoff.

**Exit:** Go protected real TLS all-cipher/rollback and Rust cold grammar native both source exact PASS; new Go→Rust positive in-process trust path must be traced with versioned authenticated provenance, fresh independent Rust generation, no public arbitrary cold install, B01–B04 real/negative cases, clear early queue max+STOP/restart, Go native+Rust engine and C ABI source-exact Actions. May report partial while owner route/physical/raw OFF. No 500Mbps or product FEC positive until observed.

### M1
R1-M1-BOUNDED-EARLY-RX-BOUNDARY-010: owner-only runtime/memory staged bounded post-bootstrap RX early queue, explicit externally supplied exact Prepare RX boundary plus length/overlap disposition, 0/1/32/33 early ingress with two generations, retained frozen/unique buffer lease across Stop and late driver return. Reject any segment crossing boundary as overlap; fresh RX is not HOL-blocked by retiring scope. No Go auth assertion, no Rust main/ABI/shared CI or driver implementation.

**Exit:** Keep 80/80 prior R1 native; independently exercise pre-boundary/after-boundary/exact crossing, 0/1/32/33-cap and full early queue, Stop before/after Detach, stale ABA token, no old→new delivery or borrowed slab free; source-exact compiled-once native and worker evidence S then cursor-only H Governance PASS. The external boundary is a caller fact, NOT minted from raw Go bytes, production readiness FALSE.

### M2
R2-M2-RACK-POSITIVE-WITNESS-INDEX-008: measure/fix the remaining admitted witness-induced O(live_shadow log N) wake-index rebuild inside ReceiptState::on_receipt; under 10k live shadow and repeated authenticated positive receipts, preserve correct PTO/RACK deadlines with bounded or amortized per-event work and no full-table cost per ACK under continuous traffic. Keep hard expiry exact, 32 wake/candidate poll, old epoch/replay/uncertain debit and new fresh independent. Scope pure crates/wbd-recovery only.

**Exit:** Keep existing51/51 R2 native; add deterministic fake-mono 10k live+1/32/33 genuine witnesses, eager ACK remove, expiry and timer after forward jumps, counted actual index operations per receipt/timer and regression that prevents old O(N) rebuild on each positive ACK without losing deadlines. Show explicit bound or record measurable remaining blocker; source-exact native, evidence S and H-only own Governance. No new unauthenticated receipt authority, Go/Rust engine or invented CPU/alloc/product claims.

### M3
R1-M3-CPU-PROBE-SAME-WINDOW-015: fix test-only fec_p0_cost_tests.rs measurement boundary where /proc/thread-self/stat CPU probes per64 batch lie outside active_wall_s; avoid 100Hz quantization and instrument thread CPU and wall from corresponding observable time windows. Require physically consistent CPU_s <= active_wall_s plus bounded tolerance on one thread before quoting fresh/steady ratio. Preserve real AEAD+unique PN, actual FEC and 2 tunnels×2 directions, 192/896B, 3 active Release reps per leg, preseal outside active scope; no product FecOrigin.

**Exit:** Keep previous98/98 Debug; add synthetic test of clock/probe boundaries and negative invalid clock accounting; corrected M3 SOURCE needs new true compiled-once Rust1.85.1 Release same-job 24/24 data rows across >=1.05s warmup+3x>=1.125s/leg and one VM, publish CPU and wall window and raw sample/clock; M0 supplies exact-source workflow after M3 CODE is frozen. Reject CPU_s > wall_s*1.02, duplicate PN/fake FEC, unsupported per-packet p99/500Mbps conclusions. Evidence S/cursor-only H own Governance; if no precise clock available, mark CPU_INCONCLUSIVE, do not claim gain.

### M4
R1-M4-UDP-RX-BURST-STOP-010: stress genuine unprivileged Linux native recvmmsg UDP ingress with strictly caller-owned preallocated <=32 buffers and a 33rd packet overflow, EAGAIN/truncation/late arrival, generation-fenced lease and STOP/rotate while old packet still borrowed. Verify no frame parser/driver callback mints authenticated Go V4 lane or consumes PN and no old-generation RX leaks into new fresh dispatch; 2 independent contexts. Confine to crates/wbd-platform/r1-go-bridge owned paths.

**Exit:** Keep previous71/71 scoped native, actual unprivileged UDP exact 0/1/32/33 plus repeated burst/starvation test, stop/late accepted/uncertain callback and buffer pointer no copied payload where observable; Native compiled-once Actions SOURCE/pass + worker evidence S/cursor-only H Governance. Explicit CAP_NET_RAW AF_PACKET positive RAW_RX_NOT_RUN unless truly observed, no OS privileges, physical/product/WindowsARM/500Mbps claims.


## Rules / nonqualifications
M0 alone owns exact trusted Go V4 session callsite, Rust engine owner admission, root workflows, main integration and production enablement. Worker contracts stay unchanged; M3 cannot mint positive production FecOrigin, M2 no authenticated receipt constructor from wire, M1 RX boundary is external and not credential authority, M4 receives only untrusted pre-AEAD bytes. Previous scoped worker runs never imply P1–P3, real raw AF_PACKET positive, native Windows/ARM, business first-packet, 500Mbps, p99, CPU-s product or physical tests. Stop on unknown source/branch or policy drift rather than broader edits. Do not repeat invalid old M3 Release runs.

## 2026-10-15 治理整理：原 registry 任务原文

仅归档详细任务，不撤销本轮分配。当前进展始终读取角色分支 cursor。

### M0

R0-M0-V4-PROTECTED-OWNER-COMMIT-023: Main-only bridge that accepts an actual Go V4 authenticated protected ColdSnapshot exclusively through the trusted session/handshake callsite and installs one fresh Rust ScopedOwner generation with exact PrepareTransition/protected reply/DetachTransition/CommitAdmission transaction ordering, bounded early RX and TX seq ownership, fail-close on invalid/stale/overlap and Stop-held lease. A self-consistent 248B cold bundle is never authentication. Default production ABI remains features0 until actual E2E test and safety signoff.

完成条件：Go protected real TLS all-cipher/rollback and Rust cold grammar native both source exact PASS; new Go→Rust positive in-process trust path must be traced with versioned authenticated provenance, fresh independent Rust generation, no public arbitrary cold install, B01–B04 real/negative cases, clear early queue max+STOP/restart, Go native+Rust engine and C ABI source-exact Actions. May report partial while owner route/physical/raw OFF. No 500Mbps or product FEC positive until observed.

### M1

R1-M1-BOUNDED-EARLY-RX-BOUNDARY-010: owner-only runtime/memory staged bounded post-bootstrap RX early queue, explicit externally supplied exact Prepare RX boundary plus length/overlap disposition, 0/1/32/33 early ingress with two generations, retained frozen/unique buffer lease across Stop and late driver return. Reject any segment crossing boundary as overlap; fresh RX is not HOL-blocked by retiring scope. No Go auth assertion, no Rust main/ABI/shared CI or driver implementation.

完成条件：Keep 80/80 prior R1 native; independently exercise pre-boundary/after-boundary/exact crossing, 0/1/32/33-cap and full early queue, Stop before/after Detach, stale ABA token, no old→new delivery or borrowed slab free; source-exact compiled-once native and worker evidence S then cursor-only H Governance PASS. The external boundary is a caller fact, NOT minted from raw Go bytes, production readiness FALSE.

### M2

R2-M2-RACK-POSITIVE-WITNESS-INDEX-008: measure/fix the remaining admitted witness-induced O(live_shadow log N) wake-index rebuild inside ReceiptState::on_receipt; under 10k live shadow and repeated authenticated positive receipts, preserve correct PTO/RACK deadlines with bounded or amortized per-event work and no full-table cost per ACK under continuous traffic. Keep hard expiry exact, 32 wake/candidate poll, old epoch/replay/uncertain debit and new fresh independent. Scope pure crates/wbd-recovery only.

完成条件：Keep existing51/51 R2 native; add deterministic fake-mono 10k live+1/32/33 genuine witnesses, eager ACK remove, expiry and timer after forward jumps, counted actual index operations per receipt/timer and regression that prevents old O(N) rebuild on each positive ACK without losing deadlines. Show explicit bound or record measurable remaining blocker; source-exact native, evidence S and H-only own Governance. No new unauthenticated receipt authority, Go/Rust engine or invented CPU/alloc/product claims.

### M3

R1-M3-CPU-PROBE-SAME-WINDOW-015: fix test-only fec_p0_cost_tests.rs measurement boundary where /proc/thread-self/stat CPU probes per64 batch lie outside active_wall_s; avoid 100Hz quantization and instrument thread CPU and wall from corresponding observable time windows. Require physically consistent CPU_s <= active_wall_s plus bounded tolerance on one thread before quoting fresh/steady ratio. Preserve real AEAD+unique PN, actual FEC and 2 tunnels×2 directions, 192/896B, 3 active Release reps per leg, preseal outside active scope; no product FecOrigin.

完成条件：Keep previous98/98 Debug; add synthetic test of clock/probe boundaries and negative invalid clock accounting; corrected M3 SOURCE needs new true compiled-once Rust1.85.1 Release same-job 24/24 data rows across >=1.05s warmup+3x>=1.125s/leg and one VM, publish CPU and wall window and raw sample/clock; M0 supplies exact-source workflow after M3 CODE is frozen. Reject CPU_s > wall_s*1.02, duplicate PN/fake FEC, unsupported per-packet p99/500Mbps conclusions. Evidence S/cursor-only H own Governance; if no precise clock available, mark CPU_INCONCLUSIVE, do not claim gain.

### M4

R1-M4-UDP-RX-BURST-STOP-010: stress genuine unprivileged Linux native recvmmsg UDP ingress with strictly caller-owned preallocated <=32 buffers and a 33rd packet overflow, EAGAIN/truncation/late arrival, generation-fenced lease and STOP/rotate while old packet still borrowed. Verify no frame parser/driver callback mints authenticated Go V4 lane or consumes PN and no old-generation RX leaks into new fresh dispatch; 2 independent contexts. Confine to crates/wbd-platform/r1-go-bridge owned paths.

完成条件：Keep previous71/71 scoped native, actual unprivileged UDP exact 0/1/32/33 plus repeated burst/starvation test, stop/late accepted/uncertain callback and buffer pointer no copied payload where observable; Native compiled-once Actions SOURCE/pass + worker evidence S/cursor-only H Governance. Explicit CAP_NET_RAW AF_PACKET positive RAW_RX_NOT_RUN unless truly observed, no OS privileges, physical/product/WindowsARM/500Mbps claims.
