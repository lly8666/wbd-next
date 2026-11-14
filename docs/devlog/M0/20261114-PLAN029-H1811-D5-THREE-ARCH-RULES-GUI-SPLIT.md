# PLAN029 H1811｜D5 规则规模和真 Windows GUI 配置并行，避免旧模式矩阵

- 一份冻结 SOURCE：用独立测试文件 `tools/m0_plan029_h1811_d5_large_rules.rs` 的 `#[path]` **直接引用当前生产 Rust `v4_client_split.rs`**，本机 rustc 1.85.1 各编译一次：Windows2025/x86、Ubuntu24/x86、Ubuntu24/ARM64。两条新测试验证 10,000 条 CN exact/suffix 域名匹配及未知域名、10,000 个不相连 CN /32 interval O(log N) 查找与海外 A/Tunnel DNS 对 CN IP/Direct业务的并集语义、活跃flow pin不热迁移。只记录冷构建/查询毫秒和纯逻辑，不虚构 OS route 个数、RSS/p99 或业务出网。
- 另一个独立 Windows2025 Action 复用现有 H1663 的真实 WinForms/当前源码 Go CLI/Rust DLL 同源一次构建，**新增**实际编辑并保存 `route-mode=bypass-lan-cn`（含 CN IP＋域名策略）、两个单值DNS、Direct flow quota，再切 `all` 验 CLI 实际读回、切回 CN/关闭表单重开验保存值。仅真实 UI+Go config，不把保存/只读preflight当 OS Applied，也不声称 Game4 的CN分流已接实网。
- 与 SOURCE c39 H1808 两出口真实业务和 SOURCE 00e H1809 OS恢复正交；无新 native 业务 Action、无七模式矩阵、无极限负载。D5 GUI-origin signed network、P1/P2 实测及 D4 IPv6 真覆盖仍未完成。

```feature-impact
{"kind":"none","ids":[],"reason":"New three-architecture source-linked pure 10k rule scale test and extended original WinForms/Go config-only route-mode assertions; product runtime/config/default unchanged."}
```
