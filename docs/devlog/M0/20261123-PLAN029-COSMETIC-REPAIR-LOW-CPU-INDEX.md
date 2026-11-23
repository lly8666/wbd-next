# M0 PLAN029 · 2026-11-23 机会式重传仅保留外观，削减无效热路径

## 用户目标与现行门槛
- 用户明确：外层冻结密文最多一次“表演式”重传用于 TCP-like 外观，**不是业务可靠修复机制**。优先低 CPU、首发无 HOL；不主动为维持精确比例制造丢包、重复健康包、伪造 ACK 或新 PTO。
- 2026-10-23 历史高损 30% 目标 R/F≈9%、R/C≥6%；2026-10-30 PLAN027 已取消强制比例下限，参考 `min(0.5p,0.09)`，持续高负载硬帽 R/F≤10%。无损 0% 近零（历史允许带≤0.05%）；资源/证据不足可跳过。所有 driver uncertain 按原保守收费，F/R/C 保留真实读回。
- 旧 M2 逐 record Receipt 已废弃。保留原 ACK/SACK 外观及同 lane/epoch、原 Seq/PN/原密文、最多一次、固定 1/2 均匀抽样、8,192 PPS 与所有旧预算/Stop。

## 本次源码最小更改
1. 原 Linux GoTLS→Rust M4 copied batch 的 `OriginalOuterRepair` 以前每个首发 DATA（即使 `outer_repair=off`、抽样不入选）都执行 `OuterAckIndex::on_definitely_sent`，在 BTreeMap 新建元数据，且后续退役/到期也处理这些必不可能补发的行。现在未抽中/关闭只用 O(1) `on_definitely_sent_untracked` 推进实际已复制的 TCP seq 边界；被选中才索引，索引容量不足则不另保留冻结密文。所有首发仍正确计 F，一次机会资格/DRIVER prefix/PN 一概不改变。
2. `OuterAckIndex::on_feedback` 在每次 ACK/SACK 不再临时分配 ranges/cumulative/positive Vec；SACK 最多8项固定栈数组，累计已确认序列直接按 BTree 最早键退休，SACK 正确认按范围原地退休。真实 gap 候选每条最多原32项。
3. 累计重复 ACK 若指向没有保留 shadow 的实际首发位置，不能把后一个稀疏候选“猜测”为该缺口。只允许 ACK 正好等于索引中保留的真实头且其后还有真实 firstsend 时提名。认证、Wintun 业务独立交付、ACK 不能当业务收据不变。
4. Linux RAW RX 每批 `PureAckSack` 提示最多4项，从 `Vec::with_capacity(4)` 改固定栈数组和计数，去掉每个 DATA-only RX batch 的堆分配。>4 个 untrusted hints 直接忽略并计无效，不再索引越界。

## 事实、待验与验收
- 代码提交到 main 与 PLAN029 已有 PR #68 活动分支；当前阶段**静态逻辑已更改，产品资格未声明 PASS**。本轮 unit/native Actions 只能按各自 exact SHA 成败结算。
- 必须检查：关闭及稀疏源不会创建索引或伪候选；未抽样 head、control seq gap、三次真实重复 ACK、有效 SACK 仍有符合语义的一次候选；Windows/Linux native Rust 编译/单元；0% ON/OFF 与代表 30% R/F 和同 VM CPU-s/GiB，签名 Windows/真实 Linux 首发、接收、延迟/Stop 不退化。
- 既有 0/1/5/10/20/30% CI 若二进制与本次修复不是同 SHA，则仅为**前一版本基线**，不能冒充此次低 CPU 改动的网络验证；不以 workflow 的 static success 代替原生三机。

### 2026-11-23 · 认证后到数据触发低频重复 ACK 外观
- 发现原 Linux 接收者在未协商 SACK 且累计 ACK 卡在真实缺口时，收到新的真实 M3 认证后到段也不发重复 ACK，导致发送端原有三次重复 ACK 线索长期不产生；这是外观提示缺失，不意味着实际业务修复失败。
- 同一原生 RX batch 只记录有无真正已认证、seq 位于累计缺口之后的新段；有该正向证据才准发重复累计 ACK；仍与原 10ms 限频共用唯一发送入口。无新后到、无SACK/无累计变化、空闲时零额外控制包；没有定期 DATA PTO、随机重传、重封密文或旧 M2 逐记录反馈。
- 纠正固定四格 SACK 数组后残留的 `is_empty()` 判定：该数组长度永不为零，应以 `outer_sack_count==0` 判断是否已有真实 SACK 提示，避免丢失正常 DATA 中的原 ACK 提示。
- 新增确定性纯单元模拟“新认证后到 → 有界重复 ACK”、“无新认证后到 → 不造重复 ACK”、原缺口被补齐后恢复。实际同 SOURCE Windows↔Linux netem、CPU/GiB、R/F、双端 Stop 仍须独立测量；未验仍记 NOT_RUN。
- 对旧文档记账释义：2026-10-23 的 `R/C>=6%` 中 C 指**外层线路容量**；2026-10-30 PLAN027 把 C 用作**控制流量字节**。两者绝不可当作同一指标，新报表分别明确分母。

- 2026-11-23 branch feature-card 合规校正：原实验分支历史验证文本偏长，新增说明后超过治理单卡16KiB限制。仅压缩摘要、保留原验证明细字段，功能行为/产品代码和结论均未变。

- 2026-11-23 复核原生功能测试的来源范围：`wbd-engine` 的 native-functional engine 选择 `r1_` 前缀；新 ACK 决策测试由 `r2_m0_...` 仅更名为 `r1_m0_...`，不变更测试输入或生产行为，确保 CI 真正执行而不是误用 filtered-out 测试做证据。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Cosmetic-only ACK shadow indexes sampled copied first sends, omits OFF/unsampled tree work and temp vectors; genuine authenticated later Linux DATA gives bounded duplicate ACK even without SACK, never a business delivery receipt; no policy/default changed; native CPU/performance still unqualified."}
```
