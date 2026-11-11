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

## H1581 第一场原始失败与 H1582 修正（2026-11-11）

- 精确 SOURCE `ca9b744e34a24cb2d7637ee7396a1806473fe3ee`，Action `42992510288` **FAIL**，Windows Go、Windows/Linux Rust 和 Linux 原Go/Rust装配编译 PASS；Windows2025真实带宽场尚未进入。`tools/m0_wl_gamefec_management_route.ps1:21` 在保护 GitHub Runner 管理地址时抛出 `MANAGEMENT_ROUTE_SCOPE_REFUSED`。这不是自动租约/AES产品网络失败，也不是端到端业务PASS。原始Action不改写。
- 真实根因：新 marker 仅设置了 `WBD_WL_RUNNER_MGMT_PIN=1` 和 `WBD_WL_NATIVE_OUTER_MTU_REQUEST=default1460`，遗漏旧管理路由保护所要求的 `WBD_WL_PUBLIC_MODES=normal`。H1582只把单独H1581 marker明确映射 normal，**不**放宽旧管理路由脚本的owner/underlay/source/恢复硬门。
- 同场发现真实夹具兼容缺口：`tools/m0_plan028_h1548_mixed_os_app.py` 以前无条件断言 Alice 为 `10.66.0.2`；H1581必须使用TLS核实的自动池 `/32`。新加仅H1581 150s/loss0传入的 `--windows-auto-ip`，且只允许Windows Alice合法服务器自动池IP、所有client仍不重复；其他手动Alice场景**继续**要求 `10.66.0.2`，600s和旧剧本不改默认。Windows和WSL2进程均显式接收这一夹具参数，不能读主机环境猜测。
- 治理 `42992510203` **FAIL** 两个历史H1570/H1576测试仍查找 `tasks=...IPS[0]`、`csv_ips=...IPS[0]` 源文本；新代码引用已认证 `windows_ip` 变量是必要真实改动。相应改为检查动态调用点和旧手动默认不被丢弃，维护单元不能代替现场收发。`42992510182` 主治理 SUCCESS。
- 修订的真实 H1581 同一 Action只派 `mixed-loss0`，200ms单程0损、真实签名Npcap/Wintun + 原Go TLS/Rust + 4 Linux TUN/共享Rust服务端，五个客户端真双向UDP/TCP150s、Alice退后Bob业务继续、六owner Stop/恢复；完成后按原始strict-native-report和源码+内核实际读回判断。细节见 [H1581 first-failure evidence](../../evidence/M0/PLAN028-H1581-WIN-AUTO-AES-MIXED-20261111.json)。
- **状态依然 NOT_RUN（修复提交前）**。任何后续 Action 的 FAIL/PASS 按那个实际 SOURCE+Job 写回；本 devlog 不预写完成。
