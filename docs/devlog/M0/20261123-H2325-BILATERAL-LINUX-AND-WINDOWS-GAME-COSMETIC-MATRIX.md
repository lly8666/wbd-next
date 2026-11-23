# M0 / H2325 · 双向外层表演式重传：Linux client+server、Windows client↔Linux、Game2/Game4

> **PR #68 接班镜像，不是实测继承：** 30 项测试工作流、Linux fixture 以及签名 Windows 复用路径都在 main **`71e8304532f77236f4aa635afd9f4d004eba2db2`** 执行。本 PR 分支在镜像时产品 HEAD `47789a32964451e4e507047dd89eb962a8516e7a` 未被本矩阵重建和原生测试；两边源码不得假定相同。结果应归属其各自 `GITHUB_SHA` / 产品 SOURCE。

## 用户要求与不越权的资格范围

用户要求补齐两端双向，尤其 **真实 Linux 原生客户端** 和 Game2/Game4 的外层重传。外层重复原冻结密文属于 *TCP-like 展示*，**不是业务修复**；不可用 FEC parity、Game4 四 lane 首发复制或传输层业务重传冒充外层 R。0% 接近零；10% 长期 R/F 上限；高损约 9% 是外观参考而非硬下限。CPU 开销最小，业务 first-send 优先；旧逐 record M2 Receipt 废弃。

- 冻结产品 SOURCE：`92920fb96f2d77ca11abcfdf4a4069d24731f62b`；2026-11-23 的真实 0/1/5/10/20/30% Windows Normal 与 30% 同 VM OFF→ON 成绩见 H2324。此轮只新增夹具、Actions 编排和证据解析，**不修改产品 Rust/Go 行为/默认值**。
- **Linux↔Linux**：新 `.github/workflows/m0-cosmetic-linux-bilateral-game.yml` 一次从本次 main exact SOURCE 编译两个真正原 Go TLS GoCLI + Rust M4 客户端/服务端，hash 锁定，两个 owned Linux netns 有真实 TUN/veth/netem 双向原生业务，60s。Normal 丢包 0/1/5/10/20/30%，Game2、Game4（FEC OFF、固定6）各 0/5/30%。独立保存每个 TX role（client c2s、server s2c）的真 R/F 或真实 Game 原密文重复包数、双方业务交付/CPU、tc drops、Stop/netns cleanup。
- **Windows→Linux**：新 `.github/workflows/m0-cosmetic-win-game-matrix.yml` 12 独立原生签名 Npcap/Wintun/GoTLS/Rust/真 WSL2 场景，Game2/4 OFF/fixed6 × 0/5/30%。每场二端各 10Mbps/250ms/60s 同 mix。严格原先 SOURCE 的 Windows 签名构件 Action `45111958268`（EXE+DLL 各个 SHA、ISA-L 来源和 Linux bundle）验证，按照 commit 精确 product diff、exact fixture SHA、双端真实外层 on readback、tc、Stop。
- **缺口仍清晰**：当前 Windows 场景中 Linux **服务端**发送反向数据，但不是 Linux client→Windows server；真实 Windows 服务端原生 TX 与 Linux client→Windows server 仍 **NOT_RUN**，需要不同的可运行 Windows server 产品/环境，不得把 Linux↔Linux 或 Win→Linux 叫作该方向已验收。
- **Game 分母**：原始 Windows 和 Linux Game 多 lane 中 `outer_data_retransmitted` 或 `copied_appearance` 才是外层重复的数据包数；多 lane 首发复制和 FEC parity 必须另外保存。若该模式未在原生 STOP 暴露按 F / R 字节计数，严格 `wire_R_F=NOT_MEASURED`；不把它说成 ~9% 字节率。
- 每个场景只认确切 source、每侧非零真实损失（loss0 净掉包应零）、original TLS+Rust 已启动、真实双向 offered 与 first-received、CPU 实数、独立 Stop、无泄漏。本轮结果起始为 **NOT_RUN**，Actions 黄色也不是产品 PASS；任何失联/缺失真计数独立归环境阻塞、业务失败、观测不可得。

## 本轮工作包 30 场景（冻结夹具）

| 原生两端 | Normal 0/1/5/10/20/30 | Game2 OFF 0/5/30 | Game4 OFF 0/5/30 | Game2 fixed6 0/5/30 | Game4 fixed6 0/5/30 |
|---|---|---|---|---|---|
| Linux client↔Linux server 双向原 Go TLS/Rust | 6 | 3 | 3 | 3 | 3 |
| Windows 签名 client↔Linux server 双向原 Go TLS/Rust | 已在 H2324 (6) | 3 | 3 | 3 | 3 |

> 这里新执行为 18 Linux 原生场景 + 12 Windows/Linux Game 场景 = **30 项**；原 H2324 Windows Normal 六档不浪费重复算新试验。所有 30 项仅因真实运行结果才可逐项结算。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Add source-frozen real bidirectional Linux original TLS client/server and signed Windows client/Linux server Normal+Game2/Game4 OFF/fixed6 outer-appearance matrix; preserve parity/first-copy separation and no runtime product changes; results pending real netem Stop and CPU."}
```
