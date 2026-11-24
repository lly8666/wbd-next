# M0 外层机会式重传修复专项：2026-11-24 用户指定范围收口与双分支同步

**决定**：接受 Game2/Game4 的 Normal-v3 真实外观机会重传的*已验证工程范围*，同步至 `main` 与 `experiment/m0-029-throughput-arm-fair`，保留原有 TCP 吞吐实验分支的独立业务优化。不是将全部 Windows/物理 WAN/CPU 目标改为 PASS，且不重启已弃用的旧 M2 per-record DATA 重传。

## 产品不变量与回退

- 原 Go TLS 标准握手、原 Rust Game M4 TX/RX owner 与真实 RAW/NPF，Linux 和 Windows 已接线；使用带正向验证的 TCP-like ACK/SACK 外观提示（仅原有 AEAD/PN 允许的数据有认证活动）提名有界 frozen shadow；半量抽样、同原 PN/SEQ/密文最多一次；总组预算 9% pacing/10% 字节硬门；FEC parity 不当 repair；不新增工作线程、定时器或第二控制面。
- `--outer-repair off` 是回退开关，不回退 TLS/AEAD/generation/Replay/Stop。生产仅保留已用正反源锁 ABBA 验证的 ReceiptState v3 **初始空 wake 索引跳过**。无收益的 lazy Vec 与 BTree entry 两次尝试均已撤销；隔离原生 ACK 提名诊断未并入正式产品。
- `main` 同步采用已有专项分支的非强制快进；吞吐长期实验分支历史与独立 TCP/ARM/Windows 优化均应保留，按冲突文件逐段合并和校验。两分支实际 HEAD 与集成 CI 状态以真实 GitHub 结果为准，本段不预支后续测试 PASS。

## 本次关闭的精确资格

| 领域 | 证据与结论 |
|---|---|
| Linux 最终无插桩源码 `9d2a3230` | [Action 45209632283](https://github.com/lly8666/wbd-next/actions/runs/45209632283)，真实 GoTLS/Rust Linux x86_64 双端 netns、七场 60s（Game2 OFF0/5/30、Game4 OFF0/5/30、Game4 fixed FEC30）全部成功；真实 R/F、首次业务/Stop/cleanup |
| Windows2025 签名 NPF/Wintun↔Linux WSL2（历史 SOURCE） | `c6f48286` [Game2 OFF5](https://github.com/lly8666/wbd-next/actions/runs/45176682065) / [OFF30](https://github.com/lly8666/wbd-next/actions/runs/45176686641) / [Game4 FEC30](https://github.com/lly8666/wbd-next/actions/runs/45176691464)；`8dbda7d4` [Game4 OFF0](https://github.com/lly8666/wbd-next/actions/runs/45181672649)、[OFF5](https://github.com/lly8666/wbd-next/actions/runs/45181676755)、[OFF30](https://github.com/lly8666/wbd-next/actions/runs/45181680575)、[Game2 FEC30](https://github.com/lly8666/wbd-next/actions/runs/45182116799)，各自原生业务/Stop PASS；**最终 `9d2a323` 共享恢复优化 Windows 原生 CPU 不可继承旧 SOURCE PASS** |
| CPU 开销归因与可保留优化 | [真实 ON/OFF ABBA](https://github.com/lly8666/wbd-next/actions/runs/45194110138) Game4FEC30 多出约1.7–2.2进程 CPU秒/60s；[线程 ABBA](https://github.com/lly8666/wbd-next/actions/runs/45195689153) 新开销约81–85% TX，主要是 first-send shadow/ACK 维护，不是单次 RAW `sendto`；[两顺序 ABBA 第一组](https://github.com/lly8666/wbd-next/actions/runs/45206294548) 与 [反向](https://github.com/lly8666/wbd-next/actions/runs/45207945974) 验证仅空 wake 剪枝双侧约1.7–2.35%收益；不构造 Windows/独立 runner CPU 因果 |
| 0/5% FEC 曲线差异 | [同机 OFF/FEC ABBA](https://github.com/lly8666/wbd-next/actions/runs/45229060432) FEC5 R/F≈3.63–3.71%、OFF5≈2.40%，源自首次 source+parity 物理记录增长和 SACK 缺口提名；[隔离原生按 PN 探针](https://github.com/lly8666/wbd-next/actions/runs/45231713451) OFF5 SACK≈9.2k PN，FEC5≈36.6k PN，dupack两者≈350–400。SACK 缺口不是每 PN 真正 qdisc 丢失的证明；不因偏高而削弱 9% pacing、10% cap 或候选密度 |

## 未完成项目（不得改写成已验收）

- 最终 `9d2a323` Windows 原生 SOURCE 的整进程 CPU 与所有 Game/FEC × 0/1/5/10/20/30 交叉资格尚未实测；既有 Windows 单元通过不等于签名原生 CPU 证明。
- ARM/真实跨机物理 WAN、吞吐容量目标（例如高线 600–800Mbps）、真实窗口/发送瓶颈仍属于 PLAN029 单独的 TCP/物理资格课题；本次修复专项收口不替代它们。
- 物理每 PN netem 丢失与乱序不可由聚合 qdisc drops 或 SACK 提名替代。旧失败 / rejected CPU 微优化一律保留原 Action 作为可审计反证。
- 吞吐实验分支的 TCP ACK/NPF/queue/window 业务优化不因为本专项合入而自动取得源锁性能资格；独立优化需要自己的 A/B 和 Windows/ARM 原生证据。

**权威结构化索引**：[`docs/evidence/M0/20261124-M0-OUTER-OPPORTUNISTIC-V3-SCOPED-CLOSEOUT.json`](../../evidence/M0/20261124-M0-OUTER-OPPORTUNISTIC-V3-SCOPED-CLOSEOUT.json)。全部历史过程仍在 [20261123 WIP 开发日志](20261123-GAME-NORMAL-OUTER-REWRITE-WIP.md)（其各时点“仍 Draft/尚不合入 main”属于历史过程，不作为本次用户批准后的当前决策）。

## 2026-11-24 集成后 Feature catalog 有界历史归档

原 `outer-opportunistic-repair` 功能卡包含 37 条精确 SOURCE 关联验证记录，超过仓库单卡 16KiB 上限。**逐字节归档**完整 37 条于 [历史完整功能卡](../../evidence/M0/20261124-OUTER-REPAIR-FEATURE-VERIFICATION-ARCHIVE.json)，活跃卡保留最近 29 条与本次收口及 Windows 未验说明，未删除或改写旧 PASS/FAIL。维护自测同步更新到 Normal-v3 当前 AEAD-open 后 ACK/SACK 入账接口，既有 STOP、鉴权与无跨流 HOL 约束不降低。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Archive full 37-row source-locked history without loss; keep active feature card within strict 16KiB repository catalog limit and preserve final-version Windows NOT_RUN scope."}
```

## 2026-11-24 两分支实际集成回执

- **main** 首次按用户授权、严格非强制快进纳入 [`1acd158e2b7ab4536cdf369230ca4a96bb8f20d6`](https://github.com/lly8666/wbd-next/commit/1acd158e2b7ab4536cdf369230ca4a96bb8f20d6)，原 [PR#71](https://github.com/lly8666/wbd-next/pull/71) GitHub 已确认 Merged/Closed。随后 [`889bf9adb4f87a957f27353fe53e122256ef766a`](https://github.com/lly8666/wbd-next/commit/889bf9adb4f87a957f27353fe53e122256ef766a) 归档全部 37 条历史功能卡 SOURCE 验证、满足 16KiB 目录约束，并更新过时的 H2229 测试断言；[主线 Governance+Feature catalog 成功](https://github.com/lly8666/wbd-next/actions/runs/45299165893)，[维护自测成功](https://github.com/lly8666/wbd-next/actions/runs/45299165816)。
- **吞吐实验分支** `experiment/m0-029-throughput-arm-fair` 原 HEAD `7576830` 的 271 条本地历史全部保留；以双亲 commit [`12341395c30b5fcafa4adb651c06f611d6b0fbe1`](https://github.com/lly8666/wbd-next/commit/12341395c30b5fcafa4adb651c06f611d6b0fbe1) 合入主线 33 项专项文件、场景和历史测试工作流。在与吞吐项目共改的 `v4_embedded_go.rs`、`linux_raw_carrier.rs`、`game_linux.go` 上使用完整原 PR 补丁 + 旧 main 重放校验做三方无损合成；Go assembly manifest `result_blob` 精确改为合成后 blob。
- [`ffb19f0744ed36da29d82701a99413be8cf8d324`](https://github.com/lly8666/wbd-next/commit/ffb19f0744ed36da29d82701a99413be8cf8d324) 用第二双亲合入主线目录尺寸与 H2229 修正；[吞吐原生单元 x86+ARM 成功](https://github.com/lly8666/wbd-next/actions/runs/45298489007)、[Feature catalog 通过](https://github.com/lly8666/wbd-next/actions/runs/45299214351)、[维护自测通过](https://github.com/lly8666/wbd-next/actions/runs/45299214420)。这里只认证已完成的工作流，其他自动启动的 PLAN012/028 长期 CI 不随本专项收口自动晋级。
- **现役两分支** 的功能卡仍为 `experimental`，仅表示已合入可用源码和测试入口，不代表所有 Windows 最新 SOURCE 原生吞吐、真实物理 WAN、PLAN029 P0/P1/P2 已达独立推广门。所有旧历史 FAIL、CPU 反证及未测事实均由本 devlog / evidence 原样保留。
