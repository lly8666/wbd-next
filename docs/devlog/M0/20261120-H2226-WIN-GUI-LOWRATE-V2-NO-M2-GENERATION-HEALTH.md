# PLAN029 / H2226 — 用户校正：断链按代际 Health 分流，WinGUI 用现有低频 Quality，不恢复逐包 M2

## 用户物理观察（2026-11-20）

原 H2225 用户只描述先前两次曾在 fast.com 上传阶段被观察到断链；**用户现明确更正**：与 fast.com 本身无因果关系。有些建链后在相近时间断开并重认证，有些建链只要越过该阶段就可长期稳定、反复跑 fast.com 也不会断。不能再将大流量上行、服务器吞吐扛不住作为主因；优先查 **代际冷启动/远端已认证 retire、冷 Health 收发、最后一次有效 AEAD 唯一 PN 入站时间/90秒超时的不同连接分支**，不得把 90秒无入站写成固定连接总寿命。H2225 原 Rust 终止诊断保留；对 H2226 源码仍未有新的双端实体复现，根因 UNKNOWN。

## 现有真实低频 Quality 和 GUI 入口

- Rust `v4_native_health.rs` 已有 AEAD 后 `LegacyQuality` v3 START/CLOSE 32字节、v2 Mature Quality 摘要；`v4_embedded_go.rs` 和 `v4_windows_owner.rs` 仅 Auto 持续启用。旧每个 M3 DATA 一条逆向 M2 bitmap/ACK 已退役，**本轮绝不恢复**。用户名词“低频质量包”即此 START/CLOSE/3秒成熟报告，不是外层 TCP ACK，也不是探测业务流量。
- H2224 Windows 原 Go native 质量生产者已每2秒输出 `WBD_CLIENT_QUALITY_V2 fec_c2s=... fec_s2c=...`，但 pinned donor WinForms MainForm 仍只匹配 `WBD_CLIENT_QUALITY_V1`：真实 GUI 源码存在 V2/V1 不匹配。H2226 仅在现有来源固定的 GUI 编译装配脚本引入 V2 解析，保留 V1；上行 applied 和下行 negotiated/unknown 各自展示，永不由 C2S 猜 S2C Auto。
- Windows Rust Auto 原生线程仍独占2秒质量政策，无额外Go Auto控制 goroutine。新的 GUI 两秒读回复用 Rust 已接收低频成熟报告所累积的字段[0..4,10..13]。同代际、单调且覆盖分母完整、>=64独立 mature sources、至少1份真实低频报告、无本地容量审查才给出首发损失 **上界**。过期/无报告/censored/revision变化，显示未知。
- 低频反馈延迟估计：原发送端 Quality CLOSE 到成熟报告返回的时长减去接收端强制 **3秒成熟等待**，但仍包含双端调度和队列延时。可粗略观察波动，不是 TCP 逐样本 SRTT 或严格 RTT，WinGUI 显示“约...（低频反馈估算）”。不改变原 Auto FEC 模型、Rust协议、低频发送频率/窗口或死活阈值。
- Normal/Fixed/游戏未启用持续低频质量统计，RTT/上界未知，不可展示0。当前服务端 Auto S2C 实际档位没有经认证的 Profile 回报；WinGUI 应明确显示 unknown 而不是误报本端档位。增加此认证能力需要单独协议/兼容性评估。

## H2226 变更范围与验证边界

- Go：`m0_native_v4_rust_peer_windows.go` 仅运行时 GUI 粗粒度 readback，读取已认证质量累积计数，无 M2 per-record、无热路径回调；`m0_native_v4_peer_windows.go` 扩展只读 stats；`m0_native_v4_windows.go` 输出版本化 Quality V2 的数值或 unknown。
- WinForms：`tools/m0_plan028_h1640_win_gui_compile.ps1` 对锁定 donor MainForm 加版本V2导入和真实GUI自检用例，旧V1保留；Windows原生 GUI 仍由同源构建与 self-test 检查。
- `r0/go_overlay/assembly/manifest-plan020-m0.json` 只对四个受影响 Go overlay/result blob SHA 做精确更新；原 Go/TLS/密钥/驱动资产不改变。
- 这不是断链修复。没有服务端代码更新或新网络协议；H2225 终止 cause 及 Linux 服务端同期记录仍是区分异常代际的必要证据。H2220旧物理FAIL不改写。PLAN029正式出口 OPEN。
- 本记录在CI前写入：**Windows真GUI/Go/Rust 运行测试 PENDING、物理双端长稳 NOT_RUN**。验证结果应在正式 Actions 完成后单独追加证据，不凭代码更改宣布 PASS。

```feature-impact
{"kind":"updated","reason":"H2226 fixes native WinForms V2 quality parsing and adds approximate Auto low-frequency authenticated quality readback without restoring per-record M2 or changing protocol/Health.","ids":["gui-config-feedback"]}
```
