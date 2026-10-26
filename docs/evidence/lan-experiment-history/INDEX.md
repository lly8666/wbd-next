# LAN TLS-like / XOR / AES 混合传输：系列实验总索引

日期：2026-10-26。**归档与后续开发的项目分支：experiment/selective-tls-crypto。** 已从 experiment/lan-tail-single8-wbd-wiring-design 原样快进同步完整继承历史；此处是经过源码检查后建立的**统一资料入口**，不是聊天逐字稿，也不意味着功能已接入 WBD main。同步来历见 [SYNC_TO_PROJECT_BRANCH.md](SYNC_TO_PROJECT_BRANCH.md)。

## 已核对的归档事实

- 当前分支中存在下述历史实验的源码、工作流、最终报告、部分 JSON 状态。之前分支是连续从已有实验提交上派生的，因此当前树也继承了历史材料。
- 原始 PCAP、GitHub Actions artifact ZIP、完整 CI 日志、整段聊天逐字记录和此前临时生成的部分文件**并不在 Git 的当前文件树**。
- GitHub Actions 工作流中的原始 evidence retention 曾设为30天；Git 内有可重跑的程序、摘要和固定 run/artifact ID，但不能把外部 Actions evidence 视为永久保存。
- **真实物理双主机 LAN 和 WBD Rust 生产数据路径尚未测试/接线**。已经验证的抓包来自原生 Linux CI 环回 TCP socket。
- 讨论与修订决定的手工归纳见 [DECISIONS_AND_GAPS.md](DECISIONS_AND_GAPS.md)；并非完整逐字聊天。

## 源码、报告、设计索引（依技术演化）

| 研究/开发阶段 | Git 历史文件 | 已完成及边界 |
|---|---|---|
| TLS-like 滚动 XOR 初版 | [初版/跨平台/握手 PCAP](../lan-xor-tlslike/REPORT.md) | Rust/Go 独立测试，非正式产品数据面 |
| 64 位展开 XOR | [优化与抓包](../lan-xor-word-optim/PERF_AND_PCAP_REPORT.md) | 比较相同线缆字节的 u64 优化 |
| 公开 PN 重复 XOR | [PN XOR](../lan-xor-pn-mask/FINAL_REPORT.md) | 不同 PN 不同包字节，非加密算法 |
| 可信分类的混合 AES + PN-XOR | [AES 回退对照](../lan-hybrid-tls-xor/FINAL_PERF_REPORT.md) | 使用理想分类 oracle，未实现 WBD 真分类 |
| 真 TLS 握手后的混合 wire 对照 | [混合线缆抓包](../lan-fastgate-mixed-wire/FINAL_REPORT.md) | 双架构网络与 CPU 证据 |
| 99% 快速路径 | [99% 对照](../lan-fastgate-99pct/REPORT.md) | 99/1 的数据面理论成本 |
| 11–21 秒门控 / padding | [边界门控设计](../lan-gated-boundary-pad/DESIGN.md) | 关注 Finished/流边界，不是强制延迟业务 |
| 移除人工重发 ClientHello | [真实重传实验](../lan-flowstart-no-synth-retrans/FINAL_REPORT.md) | 不把人工注入重发视作自然重传 |
| 8B PN 中隐蔽 mode bit | [HP mode 成本](../lan-hp-mode-cost/FINAL_REPORT.md) | x86/ARM 6轮 Go A/B；后来方案不再复用此 PN |
| VMess none / zero 机制与 WBD | [VMess 成本](../lan-vmess-none-compare/FINAL_REPORT.md) | 对照 SHAKE128 2B 长度掩码，业务载荷直传；**并没有实现完整 WS 性能测试** |
| PN-XOR 批量处理 | [完整 XOR 加速](../lan-pnxor-optimized/FINAL_REPORT.md) | 32B 展开与 Go XORBytes same-wire，对照前缀明文风险 |
| 2B marker + 尾部 1B/8B XOR | [首版尾部实验](../lan-tail-marker-rolling8-cost/FINAL_REPORT.md) | 历史上有重复 TLS 头的错误设计，保留供溯源 |
| **单层原 TLS23 头 + 最后8字节** | [修正版原生测量](../lan-tail-one-header-8byte/FINAL_REPORT.md) | **当前选定线缆设计**，原内层 AEAD 可在逆变换后验证 |
| TCP loopback 捕获 + 真实 TLS13 对照 | [PCAP 与自动解析报告](../lan-tail-single8-pcap/FINAL_REPORT.md) | 实际 tcpdump / tshark 完成，100条中80 fast/20 AES，0第二层头 |
| **接入 WBD Rust 原 TCP-like** | [WBD 接线设计](../lan-tail-single8-wbd-integration/DESIGN.md) | 当前仅设计：Go认证/M1 slab/M4 Raw复用，**未实现正式产品** |

## 可重跑的核心生成程序

- HP/PN 性能：tools/lan_hp_mode_cost_test.go、tools/lan_hp_mode_cost_analyze.py、tools/lan_pnxor_opt_test.go。
- VMess none/zero 对照：tools/lan_vmess_none_vs_wbd_test.go、tools/lan_vmess_none_vs_wbd_analyze.py。
- 2B 尾标：tools/lan_tail_marker_rolling8_test.go、tools/lan_tail_marker_analyze.py。
- **当前单层 + 尾部8B：**tools/lan_tail_single_header_8bytes_test.go、tools/lan_tail_single_header_analyze.py。
- **真实 TCP PCAP：**tools/lan_tail_single_header_capture_test.go、tools/lan_tail_single8_pcap_analyze.py。
- 更早的 TLS13/fastgate/retrans/padding 研究脚本仍见 tools/lan_xor_*、tools/lan_fastgate_*、tools/lan_flowstart_*、tools/lan_delay_boundary_pad_*。
- 自动化工作流：.github/workflows/lan-*.yml；可按各报告的确切 run ID 验证同一源码的已跑结果。

## 代表性原生 CI 和外部资产（当前分支仅存链接与复现脚本）

| 证据 | 固定 GitHub Actions 运行 |
|---|---|
| PN HP x86/ARM 6轮原始及复核 | [40200979162](https://github.com/lly8666/wbd-next/actions/runs/40200979162) |
| VMess none x86 / ARM | [40257276765](https://github.com/lly8666/wbd-next/actions/runs/40257276765)、[40257280780](https://github.com/lly8666/wbd-next/actions/runs/40257280780) |
| PN-XOR 批量优化 x86 / ARM | [40259222110](https://github.com/lly8666/wbd-next/actions/runs/40259222110)、[40259225987](https://github.com/lly8666/wbd-next/actions/runs/40259225987) |
| 尾部标识旧版 + 独立归档审计 | [40265434221](https://github.com/lly8666/wbd-next/actions/runs/40265434221)、[40265437976](https://github.com/lly8666/wbd-next/actions/runs/40265437976)、[40265674143](https://github.com/lly8666/wbd-next/actions/runs/40265674143) |
| 单层 TLS 头 + 尾部8字节 x86/ARM | [40266693532](https://github.com/lly8666/wbd-next/actions/runs/40266693532)、[40266697434](https://github.com/lly8666/wbd-next/actions/runs/40266697434) |
| 完整真实 TCP loopback PCAP (201449B) | [40268297939](https://github.com/lly8666/wbd-next/actions/runs/40268297939)、artifact 12627636543 |
| 同 PCAP TShark 无提示自动识别与强制解析对照 | [40268945000](https://github.com/lly8666/wbd-next/actions/runs/40268945000)、artifact 12626843821 |

## 当前采纳的需求及仍未完成部分

- 明确**无需复用 WBD protected PN**；2B 尾部标识；**最后8字节而不是8位**的滚码 XOR。
- 已确认的完整 TLS23 原记录保留唯一原 5B TLS 头，修改 length +2 并追加标识。AES fallback（非23或指定重传）只生成一层新的 TLS-like 5B 头，追加16B GCM tag与2B marker。
- FEC/GameMode 暂不接，仍需要 Go 已认证协商和 RAW carrier 复用。当前 Rust product 未接线。
- 当前 TUN 接收的是完整 IPv4 包（一般以45开头），不能直接把其 payload 视作完整TLS记录；若保持VPN IP隧道语义，必须在 quick-path 还原原 IP/TCP 头，否则只2B marker不可能还原所有 IPv4 数据。
- 以前所有 rolling/PN XOR 都是公开可逆混淆而非保密、认证或防重放；fast-path 尚无 WBD 层完整性认证。

## 归档缺口（需坦率区分）

**已进入 Git：**多数实验源码、基准、工作流、报告、重要决策、当前接线设计。

**尚未进入 Git：**全部聊天的逐字记录、所有临时文件/图片、完整原始 PCAP/ZIP、全部 CI 原始日志字节、过期后仍可访问的 artifact、真正双主机 LAN 结果以及实际 WBD product Rust Tail8 编解码器。相关材料只以可复现脚本、摘要及短期 GitHub Actions 链接间接留存。

**后续规范：**每次改动附源码 commit、测试 command、运行编号、原始证据归档位置和保存期限、已知失败、风险及最终结论；不能把旧 CI 当成新提交的验证。

当前总状态：**继承了丰富的实验开发文件，关键设计结论可追溯；完整逐字聊天与所有原始生成物尚未永久存档。**
