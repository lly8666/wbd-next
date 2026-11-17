# PLAN029B H2127｜B4 原生产三代真实验收 PASS；工作流误沿用旧双向TCP回执导致整轮 FAIL

[原 Action44150334492](https://github.com/lly8666/wbd-next/actions/runs/44150334492) SOURCE `534b7ba84af901492f571334a76ed510dad093da` 原始 Windows2025/WSL2 Normal **产品场景 PASS（进程退出码0）**：`WL_PUBLIC_REAL_MODE_RESULT normal PASS`、`WL_PUBLIC_REAL_MODE_BATCH PASS`。原ZIP `14358594070` SHA256 `d7b6dbd2d1ae3af2630908ecaa04f9af7c8a4e1edba61d4321e07a5a023dd34f`、28成员CRC PASS；原 `mode-results/normal/report.json` 同源 Go/Rust/fixture、`mode_public=PASS_ACTUAL_WINDOWS_LINUX_NATIVE_normal`、`stop=PASS_BOTH_OWNED`、`tcp_duplex=PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP`。

同一原场景三代真正 WinForms GUI Connect/Stop，逐代 OS Applied/WAL回收 3/3，原TLS端口41031/41032/41033和Linux M4三次、外层1460/内层OS1389、SYN/SYNACK MSS1420；高级CN物理DNS+FakeIP直出、普通CN物理DNS+真A走Tunnel、all通过Tunnel DNS+真A走Tunnel；Linux原内核UDP DNS/业务6项实收，旧FakeIP应用无回复且物理/TUN AF_PACKET旧假地址出包0。普通 Windows↔Linux UDP 确认，原 H1762 单向真 Windows Winsock TCP→Linux TUN listener receive 36字节+reply、Windows echo=TRUE；随后最后一次原 Windows/WSL Stop 完成。

**CI原native job仍FAIL，不能涂成Action PASS**：来源为 `.github/workflows/m0-wl-public-normal-full.yml` PowerShell 收口校验，仅允许旧通用 `PASS_ACTUAL_TWO_OS_KERNEL_TCP`；真正原B4已按本包范围走 `PASS_REAL_WINDOWS_TO_LINUX_TUNNEL_TCP`，旧028 Linux→Windows入站方向不在本包。新 [SOURCE cde9e79](https://github.com/lly8666/wbd-next/commit/cde9e7921737aad6f332a10fb738e2a4d764e9dd) 只增加 B4专属严门：同源三GUI Applied/Stop、原Linux出口、旧假IP0、实际原TCP、MTU/MSS与两端Stop；所有其他场景原严格双向TCP验收保留。[新 Action44153223434](https://github.com/lly8666/wbd-next/actions/runs/44153223434) 收集时在运行，未得最终结论。

B4真实产品核心已PASS_SCOPED；只有新签名原CI最终全绿才可声明本阶段整体验收；Game2/Game4、B5真实同VM≤10Mbps CPU/实际GiB/RSS/p99仍 NOT_RUN。029/029B OPEN，030未启动。旧 red Actions与物理资格不覆盖。

```feature-impact
{"kind":"none","ids":[],"reason":"H2128 only exact B4 post-native CI verifier; product runtime and other-mode TCP hard gate unchanged, B4/Games/B5 not promoted by docs."}
```
