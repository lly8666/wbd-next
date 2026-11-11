# PLAN028 M0 H1588｜30%真实丢包下 Windows 冷TLS + 真正Linux内核反向业务复验（2026-11-11）

**提交流程前：NOT_RUN；PLAN028 IN_PROGRESS。**旧 `6207858bac1d2a74bd560f7e2b7f649df887c066` Action `42942358907` 冷 TLS 首因FAIL历史保留。最近 `e207fa95bf861cc63a8bf3b0007db2dae644c7dc` H1583 Action `42996888234` 在真正Windows2025签名Npcap/Wintun、WSL2 Linux原始Go credential TLS443、实测物理双向30% loss且200ms单程下，**真实受保护TLS已通过**（两边 Rust M4、ChaCha cipher1/手动 `10.66.0.2/32`），但其首次 Rust native 20s `TXCopied42 RXDelivered0 TXAfterRX0 Rejected17 WorkerError0`，共享Rust服务端 `routed=0 reader_joined=1`，Action overall **FAIL**。原代码 `h1579` 因 `probe=false` 完全没有启动Linux内核反向UDP应用，故不足以判定真正丢包下首交付是否可用；其WAL/netem/WSL恢复结果保留、`Windows READY` 和 OS Applied 未完成，不能归到TLS失败，也不能写成已经修复。

本轮代码 `tools/m0_plan028_h1548_one_windows_four_linux_600.py` 在 H1584 已完成同一真实核验路径的修正：`if probe or h1579` 时创建原 `10.66.0.1:45941` **真实Linux TUN UDP socket**；H1579只在原 TLS/Linux M4 ready日志出现后，向真正手动认证租约 `10.66.0.2/32` 最多发送70个原 UDP datagram（0.15s间隔）。H1579启用260s真实helper生命周期以容纳有界160s冷认证观察；不注入任何 fake ACK、M2/M3 receipt、Rust缓冲或伪造Win Ready。只有两个OS真正初始认证、Rust唯一首到及反向业务证明、实际Wintun /32 OS读回、Windows独立 Stop、共享Rust服务端 reader_joined1、netem/WSL桥/WAL恢复全部通过，才允许输出专门的 `PASS_SCOPED_H1579_WIN30_COLD_TLS_M4_OWNED_STOP`；不要求用30%损包完成另4 Linux客户端或200Mbps压力。

H1588单场仍使用**原有**工作流 marker `[plan028-h1579-win30-cold-auth]`，只选 `mixed-loss30`、一台Windows2025和一台Linux共享server、200ms单程、150/600s四Linux业务明确 **NOT_RUN**。本提交额外在原有 `tests/test_m0_plan028_h1579_win30_cold_auth_scope.py` 添加源级确保真的绑定Linux kernel socket、指定受保护原始手动地址、先启动UDP helper后安装netem、真实发包并验证原始入站数据（避免再次漏掉对首反向硬门的必要输入）；旧源级测试通过不是产品结果。

与此同时 H1586 SOURCE`dd82db7e` Action `43000134310`（Windows原生自动IP/AES256+4Linux 150s）和 H1587 SOURCE`3b6d53c3` Action `43001721886`（双Windows手动AES128/ChaCha共存）分别在独立VM进行。当前H1588是第三个**不同**的原生网络场景，而非重复任何正在运行或通过的场景；一Action一个场景。不提前进入029/030。

```feature-impact
{"kind":"none","ids":[],"reason":"H1588 only strengthens scoped source lock for existing true Windows2025 30% cold-TLS original Go/Rust + genuine Linux kernel reverse acceptance, not product code/default or new control capabilities."}
```
