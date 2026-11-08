# PLAN028 H1404｜SOURCE差异严格复用 L3 ARM64 与 Windows 五原生短测

2026-11-08。在 H1403 单项 Windows 真 Game4+FEC 宽限回归运行期间做独立**离线**资格收口，不新增 network Action。

- 由 GitHub commit compare 精确确认，从两条完整原始 native ARM64 1800s Go TLS/Rust L3 资格 SOURCE `4444328d...` 到当前 `d3093607...` 超前10提交，其中实际产品 Rust 仅改 Windows 专用 `crates/wbd-engine/src/v4_windows_fec2_owner.rs`，未改原 Go 认证、Linux Rust Game/FEC 热数据面、生命周期逻辑。现行 Linux ARM64 L3 场景 0告警、最大有效应用空洞 50/120ms、十条真实 veth permanent L2 peer MAC、Erin 30% DATA netem、非零真实 ISA-L 编解码、五真实 Stop 源 SHA 不变，记为 **SOURCE_SCOPED_REUSABLE**；不谎称新 SHA 编译过已测试产品，也不据此给 Windows 改动 PASS，原 H1389 性能 FAIL 保留。证据 `docs/evidence/M0/PLAN028-H1404-SOURCE4444-TO-D309-L3-LINUX-UNCHANGED-SCOPE-20261108.json`。
- 独立 [Windows Action42483793718](https://github.com/lly8666/wbd-next/actions/runs/42483793718) 五个真实 Windows signed Wintun 原 Go TLS/Rust AEAD-to-native UDP 短模式 job Normal、Fixed、Auto、Game2、Game4 均 SUCCESS。五个 ZIP 各2文件、CRC全 PASS，固定和Auto还真实通过丢失原 FEC source 的 RS16 修复，Game lane 阻断首次/反向业务仍到 app。各 mode 以 **PASS_SCOPED** 录入；它们自报 `sustained_10mbps=NOT_RUN`、`official_public_mode_os_applied=NOT_RUN`、host WFP NOT_RUN，不自动放大为 Windows 真多客户端或 native 运行时 ISA-L 的全资格。精确原 ZIP SHA/每模式 scope 见 `docs/evidence/M0/PLAN028-H1404-SOURCEE69-REAL-WINDOWS-FIVE-MODE-SIGNED-WINTUN-SCOPED-20261108.json`。
- 当前 Windows 来源 `e69e40f3` [主 Action42483793673](https://github.com/lly8666/wbd-next/actions/runs/42483793673) 的原失败为测试立即要求不存在的旧代 Stop 标记；实际服务器明确安排10–20s实际宽限，已在 H1403 仅修夹具，新的单场原生行动在途。原 Action FAIL、full product exact old Stop NOT_TRIGGERED 不提前洗白。原 Windows 固定 ISA-L release build/unit资格和 ARM64 full L3均按分开 SOURCE 保存。

```feature-impact
{"kind":"none","ids":[],"reason":"Original ZIP-qualified Windows five short packet modes and unchanged Linux L3 source-delta evidence; no product feature or protocol changes."}
```
