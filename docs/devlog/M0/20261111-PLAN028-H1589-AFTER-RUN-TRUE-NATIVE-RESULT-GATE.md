# PLAN028 M0 H1589｜H1586 true 150s signed Windows AES256 原始 PASS 与通用后置门误判修正

日期：2026-11-11。PLAN028 **IN_PROGRESS**。本记录只整理已完成 Action 与修正 CI post-gate，绝不改写旧 Actions 的 overall conclusion。

## H1586 SOURCE dd82 的真实实证（与 Action overall FAIL 严格分开）

确切 SOURCE `dd82db7ea529cfb7ed162ca665174c5df95a2ead`，Action `43000134310`，native job `130456547588`，原始 artifact ZIP `13846582275` SHA256 `39962ca1be96761fcd3a136f2083911f0a76b381b8bf5c4a0702e8d466fb5425`。从 `h1548-loss0-strict-native-report.json` 和五客户端业务独立 app 日志读取：

- 真 Windows2025 signed Npcap/Wintun 原始Go cert/credential TLS443+Rust M4，Alice `auto_lease=true` 真服务端 /32 `10.66.0.207/32`，Rust protected cipher ID3 AES-256-GCM，实际签名Wintun OS IPv4读回 `10.66.0.207`。Linux内核 TUN UDP 在认证后向此 /32 真送包并通过真实首反向。
- Linux四个独立账户经各自原始Go TLS、共享Rust M4：Bob ChaCha `10.66.0.138`、Carol AES256 `10.66.0.187`、Dave ChaCha `10.66.0.233`、Erin AES128 `10.66.0.132`。**同一服务器同时运行三种AEAD**，不是服务器全局改码也不是只在CLI选项读字符串。
- 0% netem丢包、真实单程200ms；五个OS kernel app **真双向150s UDP/TCP**。Alice UDP C2S `113657/113657`，S2C `113662/113662`；其余四client计数及TCP零invalid详见 `docs/evidence/M0/PLAN028-H1586-SOURCEDD82-WIN-AUTO-AES150-NATIVE-PASS-SCOPED-20261111.json`；Bob在Alice owned Stop后真实核UDP再收到4包。六owner Stop：Windows WAL无残留；Linux Rust shared TUN `routed=456217 unrouted=0 reader_joined=1`，WSL桥复原、Windows eth0 netem清除。
- 原生 strict `status=PASS_SCOPED_H1581_WIN_AUTO_AES256_LINUX_THREE_CIPHER_TCP_UDP_150S`，原生进程 `native_exit=0`，专门 PowerShell hard gate `H1581_REAL_WINDOWS_AUTO_AES256_LINUX_THREE_AEAD_150S_UDP_TCP_SIX_OWNER_STOP_PASS_SCOPED`。
- **Action整体仍 FAIL**：后置脚本通用 `if($env:WBD_WL_PUBLIC_MODES -ne 'all')` gate 错把新五客户端scoped report要求成传统一Windows+一Linux模式 `mode=normal`, `PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal` 与 `PASS_ACTUAL_TWO_OS_KERNEL_UDP/TCP`，并在新的专门 strict gate 已PASS后抛 `selected same-SOURCE native public mode lacks actual two-OS UDP/TCP/Stop proof`。旧失败必须保留，不能修改Action结果。

H1589 **仅修正该后置分发**：在传统 Normal/Auto/FEC/Windows5等既有总门之前，显式选择 `WBD_PLAN028_WIN_AUTO_AES_MIXED_150=1` 严格检查真实结果 `source_sha==$env:GITHUB_SHA`、`status=PASS_SCOPED_H1581_WIN_AUTO_AES256_LINUX_THREE_CIPHER_TCP_UDP_150S` 和 `mode_public=PASS_MIXED_FIVE_ORIGINAL_150S`；`WBD_PLAN028_WIN_30PCT_COLD_TLS=1` 的另一个单Windows冷TLS报告单独对应 `PASS_SCOPED_H1579_WIN30_COLD_TLS_M4_OWNED_STOP` 和 `PASS_MIXED_FIVE_ORIGINAL`。两个分支只有 **已通过此前完整特定 source-locked report hard gate** 后才可通过，绝不绕过真实TLS/驱动/业务/Stop，也不混用0损与30损。传统 Normal 等原有通用硬门保留在独立 `elseif` 原样执行。

## H1587、H1588 原始失败仍独立

- H1587 SOURCE `3b6d53c30531f6820c220f9e6c23f8a23480227c` Action `43001721886`，A真实TLS/AES128与Wintun OS Ready、其 UDP/TCP工作；B 真实TLS/ChaCha认证和Rust M4、Linux server 两种cipher都安装成功，但第二台Windows原始WAL/路由阶段 `windowsclient: route is not owned; refuse to replace`，B的OS /32未安全安装、B app bind `WinError 10049`，A Stop/B继续**NOT_RUN**。不删除竞争路由、不松外国route/owner Guard。原始artifact `13846773203`。
- H1588 SOURCE `5f0ac32ba0b5d933337ed88f0b33f54da579ac9c` Action `43002178705` 真30%双向随机丢包/200ms单程。SYN/SYNACK MSS1420实证但原始标准Go credential TLS尚未通过，错误 `faketcp: bootstrap stream deadline exceeded`，Rust M4/Wintun OS和反向业务都是**NOT_RUN**。Windows/WSL/netem复原，原始artifact `13847342578`。之前 H1583同损场一次TLS通过不是 H1588 通过；需定位15s有界冷候选deadline、真实重传/统计再做不同故障隔离，不能空降PASS。

H1589 是 **postgate-source-only**：不重跑已在 dd82 真通过的150s来洗绿旧Action；此提交不带H1581/H1579真实网络marker。后续优先产品所有权与30%冷TLS恢复的独立实证；600s/250–300Mbps、30%完整业务、两1800s L3、same-account multi-installation、Android、029/030仍NOT_RUN或不在该资格范围。

```feature-impact
{"kind":"none","ids":[],"reason":"H1589 only routes two previously strictly validated source-locked Windows native scene summaries around an unrelated legacy Normal 2-OS postgate; no product changes or removal of strict acceptance requirements."}
```
