# PLAN028 H1515｜Windows5 原始 ZIP 首错：真实产品 TLS 前两道冷门

- SOURCE `add5377be702a1b4a79b8418255f550bf0a0eeac`，Action [42769807553](https://github.com/lly8666/wbd-next/actions/runs/42769807553)，Windows5 loss0 job `129676593518`，原始 ZIP artifact `13741214591`，各 binary SHA256 见证据。Linux Go/Rust build、Windows Go/Rust compile、Linux 共享服务端 `V4_PUBLIC_MIXED_MULTI_SERVER_READY` 和外层 1460 实测通过；本轮业务确实 **NOT_RUN**。
- 原始 `h1506-client-alice.log` 在 TLS 前先报 `refused unscoped Windows original Npcap guest MAC override`，明示真实 WSL host nextHop=172.29.0.1，verified guest 172.29.11.172? (原日志路由身份见 ZIP)，原本 CI-only `WBD_PLAN028_WSL_OWNED_SWITCH` 漏开。**不**把这一保护直接关闭：用既有 `m0WindowsVerifiedOwnedWSLRoute` 限 exact guest198.19.254.2、source198.19.254.1、OS 选中 ifindex25 校验，并仅在原生 Windows five Action 中启用。
- 原始 Bob/Carol/Dave/Erin 日志 `another Windows client is running or cleaning up`；独立 OS 管理确被旧 GUI 全机单例阻断。现有 H1381 只有两客户端 CI 原生 named-event 隔离；本修复**只在 GITHUB_ACTIONS + 显式五客户端环境**允许五个固定账户、别名、独立/32和 exact WAL basename，任意同别名重复拒绝；普通生产 GUI 默认全机锁不动，不新增控制平面、防护框架或修改数据面。
- 下游 Windows app `WinError10049` 是因五个客户端没有一个安装真实 Wintun /32；不以 app bind 重试掩盖原生根因。原 native 600s/TLS/M4/MTU/物理轮换/Stop 均 **NOT_TRIGGERED**，将原始 FAIL 保留。
- 排查现行 mixed 服务端得知脚本后段以不存在于 mixed 路径的旧 `V4_PUBLIC_MULTI_SESSION_READY` 计数，还以旧 `V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server` 统计 Stop。离线修成实际混合 Normal/Game 组已认证 M4 标记和 `V4_PUBLIC_SHARED_TUN_STOP generation=...` + `reader_joined=1`，要求先真传输再判定。若网络根本没触发，这些修复不能冒充 PASS。
- 按原 SOURCE manifest 构建一次并触发仅一场 loss0 Windows2025 真 Npcap/Wintun + WSL2，优先见五客户端 TLS/M4/MTU 后再跑 600s。loss30 暂不派发。PLAN028 **IN_PROGRESS**。

```feature-impact
{"kind":"updated","reason":"PLAN028 Linux original shared manual-account server startup now proven; Windows actual native five-client pre-TLS WSL2 guard and global GUI slot isolation failed. Gate exact CI-only five OS owners and restore real mixed-mode M4/Stop reporter markers without relaxing production defaults.","ids":["tls-auth-multiclient"]}
```
