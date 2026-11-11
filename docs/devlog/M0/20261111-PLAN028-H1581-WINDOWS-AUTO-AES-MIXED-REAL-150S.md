# M0 PLAN028 H1581｜单场 Windows 真 AutoLease AES256 + Linux 三 AEAD 混跑（2026-11-11）

**派场前状态：NOT_RUN；后续仅按 Action 原始结果判定。PLAN028 IN_PROGRESS。**
以 H1580 Windows 自动租约/record cipher原Go TLS→Rust→Wintun接线和已通过的 SOURCE813 Windows Go编译为基础，复用 H1548/H1574/H1577 真实混合客户端夹具，不新造协议、信号或输出假 PASS。

**精确触发：**push 主线提交 message 包含 `[plan028-h1581-win-auto-aes-mixed-150s]`，`.github/workflows/m0-wl-public-normal-full.yml` 的 `native-public-two-os` matrix 仅有一个 `mixed-loss0` 场景。若有正在运行的同源/同场 Actions 不再重新派发。真实机器是 Windows2025 + 签名Npcap/Wintun + WSL2 Ubuntu 共享Linux原Go TLS443/Rust TUN + 四个独立Linux netns原生客户端。物理外层单程200ms、0%损失，不称为30%或600s；实际外层双向字节/150s six-app均源自OS与内核。调用原 `tools/m0_plan028_h1548_one_windows_four_linux_600.py`，专属环境变量 `WBD_PLAN028_WIN_AUTO_AES_MIXED_150=1`，只切这一场，不污染旧手动/ChaCha H1577 fixture/default。

**真接线证据门：**
1. Windows Alice 不给任何静态 `--lease4` 或预设 `--tunnel-id`，单独 installation ID+username/password 自动推导身份；服务端 Alice 人工映射不提供，必须从真实 server auto pool `10.66.0.128/25` 授出 `/32`。Windows显式请求 `--record-cipher aes-256-gcm`、Normal FEC Off。原受保护 TLS→ Rust M4 的 `WBD_WINDOWS_AUTHENTICATED_NETWORK_SELECTION mode=... auto_lease=true lease=x/32 cipher=N source=original_TLS_Rust_snapshot` 必须出现并为非静态池内 /32；从实际 signed Wintun `Get-NetIPAddress` 再读一次，要与该地址逐字吻合。请求/后端值不匹配须 fail closed。
2. 四个 Linux 客户端分别独立身份、TUN、namespace、实际自动 `/32`，各自配置 ChaCha20-Poly1305、AES-256-GCM、ChaCha20-Poly1305（Game4）、AES-128-GCM（Normal固定），同一 Rust服务器同一个443端口；server实际分配的 /32 不得冲突。已有H1577 mix lane/FEC基础上新增 Windows AES256真实互通，不将不同终端伪装成两个假会话。
3. Alice在所有Linux join之前预先做4个真实UDP回声；全部客户端+ server 150秒实际双向 UDP/TCP 消息，≥100真实独立UDP/方向/客户端、≥98% delivery、TCP 双向每端≥60有效帧且 invalid=0、最大有效交付空洞<3000ms。终点Windows主动Stop，四Linux真实业务仍活着且Bob仍收到4 UDP；然后四Linux独立Stop，shared Rust server reader Stop，WAL、Windows netem、WSL owned bridge/veth严格恢复。
4. 最终读 `result/wl-public/h1548-loss0-strict-native-report.json` 的完整 `source_sha`、OS收发、`h1581_windows_protected_auto_lease`、`h1581_windows_actual_signed_wintun_os_ip`、`h1581_windows_rust_cipher_readback`、五client TCP/UDP、六owner Stop；只有真实成功且clean才输出带 `TRUE_150S_FIVE_CLIENTS_NOT_600S` 的兼容 normal-report。Linux真实三套cipher来自启动配置，后续要把server/Rust各client受保护读回补足才能称独立全覆盖。

**不冒充的范围：**这是一个不同客户端参数共存代表真实场景（Windows AES256 自动IP vs Linux多AEAD），仍不是 Windows 三种cipher各自真 native、手动IP×AES128、Game2/4 Windows所有组合、Win30% cold TLS/候选失败保A/idle唤醒/1300字节近MTU大包/高压长期跑；那些需要后续按变更/旧SOURCE evidence 的精确范围核对。生成器物理服务器过载有容量边界时如实记录 first fault 和真实CPU/RSS，不要借口VM掩盖产品线程/锁问题。

**Action 开始前不写结果，不提前更改 PLAN028 状态；失败总 Action 保留原状并在单场 first fault 后修复真正缺口。**

```feature-impact
{"kind":"none","ids":[],"reason":"H1581 only adds one source-scoped native test harness/workflow and records the exact not-yet-run acceptance; no product code or feature stage/default changed."}
```
