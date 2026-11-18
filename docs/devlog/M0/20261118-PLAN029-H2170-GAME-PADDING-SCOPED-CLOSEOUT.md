# PLAN029 H2170｜Game2/4 startup-padding 真Win2025原生六场PASS_SCOPED

用户明确要求将Game startup-padding正式接线、测试并维护WinGUI/功能卡。H2167原Go TLS认证的Game2/4 cold config已以native V5传`off|tls|flows`到原Rust GameAdapter per-lane AEAD，保留V3/V4旧ABI，无新FEC/AEAD/Go热路径。FEC源符号拆出真实IPv4提议padding，Parity/Health不参与；原生NPF成功拷贝后而非Stage时才计`copied_records/copied_bytes`。原 WinForms 传输页单一选项、profile旧bool迁移、重连与帮助字段更正，正式assembly result blobs校验通过。

## 签名真实网络结果

原SOURCE `81998f91d183c722be932543be6434c1fd31be57`，[Action 44250162599](https://github.com/lly8666/wbd-next/actions/runs/44250162599) **completed SUCCESS**；Linux source-locked original Go/Rust build SUCCESS，两独立Windows2025/WSL2/Npcap1.88/Wintun原生作业：
- [Game2 FEC off job134621109973](https://github.com/lly8666/wbd-next/actions/runs/44250162599/job/134621109973)：off 0条/0B，tls 2条/837B，flows 34条/7663B；三代各真实UDP/TCP、Stop PASS。
- [Game4 FEC fixed job134621109899](https://github.com/lly8666/wbd-next/actions/runs/44250162599/job/134621109899)：off 0条/0B，tls 4条/843B，flows 70条/16391B；三代各真实UDP/TCP、Stop PASS。

六条`plan029b-game-padding/<side>/<mode>/report.json`源锁`source/fixture_source/product_binary_source/linux_binary_source`都等于上述SOURCE；所有子进程exit0、`app_duplex=PASS_ACTUAL_TWO_OS_KERNEL_UDP`、`tcp_duplex=PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP`、`stop=PASS_BOTH_OWNED`、`requested_original_win_mtu=1460`、原应用TCP echo与可信Linux TUN接收均真PASS。每种pad接受量<=500B/条。两Windows CLI SHA256一致 `69e9d3bcc2f4c741af28adb09a031ded5917503aef171bc126fb87924ffe0a75`，Linux SHA256一致 `9188f3941eba3dfd48831f779e0d8b73d3b31deda4c1978a1f270e11d75dcc71`。详见 [H2169签名证据](../../evidence/M0/PLAN029-H2169-GAME2-GAME4-STARTUP-PADDING-SIX-NATIVE-PASS-20261118.json) 与各Action artifact `14403424471`/`14404530810`。tls arm真实Windows内核TCP发送的是TLS-record样式数据前缀，仅证明流识别，不是应用TLS握手。

H2168 [Action44248395979](https://github.com/lly8666/wbd-next/actions/runs/44248395979)仅cheap PASS但原生SKIPPED，不能当作网络PASS；H2169修中央native_smoke marker并对门禁加测试才真正运行。H2166最初Rust cfg/assembly/feature CI FAIL和H2167旧Windows M4冻结测试RootCAs编译FAIL保留，不涂抹。H2167 [Action44247188583](https://github.com/lly8666/wbd-next/actions/runs/44247188583) 原GUI assembly / Windows Rust419测试(包含Game2/4定向AEAD)及Go编译另SOURCE PASS；不能与H2169真网络混为同SOURCE原WinForms按钮测试。

**精确边界**：H2169仅Game2 FEC off及Game4 fixed×三档；Game2 fixed/Game4 off填充排列、真实Game WinForms GUI按钮→OS/NPF三档一代、Linux主动Windows入站TCP、全宿主IPv6、同VM CPU/p99仍NOT_RUN。WinGUI字段/CLI是正常产品配置可用，但GUI交互真网络需独立验收。旧H2162 Game20/20分流与H2135 Normal三代WinForms原生各自SOURCE保留。029/029B日常PASS_SCOPED，完整技术D1–D5/P1–P2和029B§6–7 OPEN；030 NOT_STARTED。此次只整理证据、卡片、入口、cursor，不重编/重跑原生产二进制。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"Promote only H2169 six signed native original Game startup-padding scenes with exact SOURCE, authentic NPF copied bytes, MTU, TCP/UDP and owned Stop; correct stale handoff status without claiming Game WinForms button qualification."}
```
