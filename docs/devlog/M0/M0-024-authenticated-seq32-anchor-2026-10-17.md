# M0-024：受保护原路径 seq32 长跑可信锚点（2026-10-17）

- **why_now**：当前main已有原Go TLS凭证→Rust owner→Linux raw/TUN的持续双向业务与同VM P10；但原`background_raw_once`每DATA把wire seq32相对固定Go bootstrap `rx_boundary:u32`扩展。长期运行超过约半个32位序号空间后，合法后继DATA可能被错误延伸/拒绝（不能归因旧80秒中断）。属于024真实热路径的正确性安全栅栏，不是重开已完成CPU优化。
- **实质源码**：只改M0的`crates/wbd-engine/src/v4_embedded_go.rs`。新增单session `rx_seq_anchor:u64`、初始可信Go boundary；M4原tuple/checksum验证和`extend_seq32`仅形成候选；仅当原M3 AEAD+PN去重的`AuthenticatedRxReport.link_ready==1`时推进高水位，不由未认证TCP头、重复、无效LINK或失败seal推进。Stop/rotation新Entry独立，不新建session/worker；移动参考不追旧包，不因旧洞等待fresh。64位加法溢出明确失败。
- **精确验证**：新增同一生产辅助函数的seq32回绕、半空间固定boundary误扩展、认证成功/失败、重复和溢出向量。原`m0-v4-native-owner-probe.yml`、`native-regression.yml`及真实Go/Rust/Linux raw/TUN功能Actions应由此源码push触发；尚未观察run/manifest的部分为PENDING/NOT_RUN，不能以单元向量代产品PASS。相关§4 I01–I04；长业务/真实高带宽跨回绕仍NOT_RUN，500Mbps/80秒症状不作归因。
- **边界**：不改worker M1/M2/M3/M4源、生产features、Go ABI或外部机器；原配对P10的CPU正负反转INCONCLUSIVE、D10 ptrace失败和原023/超MTU开放。
- **next_action**：核对本次代码SOURCE Actions和artifact后，继续024方向-owned TX/RX真实接线/Stop-fence与ready聚合，不把修复扩展为未经证实的性能收益。

## 已返回的精确 Actions（同轮后续收据）

- 最终测试SOURCE `9249115c809933eae7ddebdd9334bbe16095bf64`、engine CODE `21a809c212ce2175b26f86468c0bc718adb7f44f`；原 Go/Rust/Linux native [run 39023910341](https://github.com/lly8666/wbd-next/actions/runs/39023910341) build 117371014730/consume 117371263021均success。新Rust测试 `r1_m0_live_authenticated_seq32_anchor_wrap_and_untrusted_no_advance` 在编译好的feature-gated原engine binary实际执行 ...ok，同job原真实Go TLS/3 AEAD/PN/raw/TUN、MTU fail-close、netlink、针对性PN0丢失PN1独立交付、开发态10s+60s双向10.0002Mbps均通过。build ZIP sha256 `1163f00f76ab0402eca6267e43fe5b95a1ba2a3f7cb2f93fa789e72d974ad304`，result ZIP sha256 `148216ba130db689d99bfe8962553cc64d542b201059882ecc011ea92e8d1f78`，详见独立SOURCE证据 `docs/evidence/M0/M0-024-authenticated-seq32-anchor-9249115c809933eae7ddebdd9334bbe16095bf64.json`。
- 证据边界：内置helper模拟快速跨界，本轮**没有**实测kernel连续写越2GiB；本次10Mbps是UNPAIRED DEV，不与旧AB/BA CPU组装收益。完整024、CPU改善、Game/FEC-on、原023、产品/物理均未通过；原D10 full ptrace FAIL保留。
- worker接入复核：M3在分配后并行更新cursor H27，代码016冻结`422a2612`，M0 native ISA-L真实Go矩阵3项run39016665239有效，Release配对CPU仍NOT_RUN；M3/M4旧Governance failure分别是moving control/incomplete ancestry审计边界，不重命名为功能失败或凭普通 main PASS 覆盖。

## H120 新审计范围失败恢复（非功能测试失败）

- H120 `381605a19e828f90cf52497cd413f572f124eab1` 的普通 Governance run [39024310202](https://github.com/lly8666/wbd-next/actions/runs/39024310202) **FAIL**；日志明确 `SCOPE_AUDIT_FAILED: cursor evidence SOURCE mismatch`，不是CODE和Native失败，也不是M3/M4旧moving-control失败。主线 `tools/scope_audit.py::check_role_metadata` 要求cursor的**所有** `evidence_refs` 都以同一个`last_tested_source`为SOURCE；H120把历史P10 AB/BA证据（SOURCE e26e5d）和新原路径native seq32证据（SOURCE924911）同时放进`evidence_refs`触发该真实结构失败。
- 修正：当前SOURCE `9249115c809933eae7ddebdd9334bbe16095bf64` 的本轮证据留`evidence_refs`；历史P10证据保持原文件和事实，但移为`context_refs`。不能把旧P10的SOURCE篡改为新提交，不重跑已通过的Go/native；另起cursor-only H提交后核实Governance。
