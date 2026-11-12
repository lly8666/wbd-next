# PLAN029 H1690｜收回真实签名 Wintun UDP 控制 / TCP SYN 失败，修正游标硬门

- [SOURCE 0f1eecd44eafc522dee7d8378040817d0c803cc4 / Action 43243971440](https://github.com/lly8666/wbd-next/actions/runs/43243971440) **FAIL**，保留原失败。Windows2025 签名 Wintun 0.14.1 / owned Win32 IP Helper `/32` / 反向 `/32` route 实际通过前置；同主机原生 TCP listener dial/accept PASS，原生 UDP listener 本机自测 PASS；由同一 Wintun 注入的 UDP 未到 listener（3s 无匹配），TCP SYN→SYNACK 仍 FAIL（6s RX 无对应帧）。此对照说明失败不是已证实的纯 TCP 独有问题，**不能证明已找到 Windows 丢包层**。
- `netsh advfirewall show allprofiles` 只读结果为 Domain/Private/Public 已开启且默认 `BlockInbound,AllowOutbound`；原 PowerShell Get-NetFirewallProfile 仍 exit1。这里没有动态 drop 来源、过滤器命中或网络栈跟踪，默认入站策略不是已证明的包因果；未创建/修改任何 WFP/Defender/第三方规则。
- 真实 artifact [13955053359](https://github.com/lly8666/wbd-next/actions/runs/43243971440/artifacts/13955053359)，ZIP SHA256 `f01f56fa6d29432da8560fbdbde99b8cbbf27a9de1d9907e40a3b96c02dfa23d`，原回执 `result=FAIL_SIGNED_WINTUN_KERNEL_TCP_SYNACK_ABSENT`、`signed_wintun_udp_ingress_control=NO_MATCHING_NATIVE_DELIVERY`、`wfp_guard=NOT_CREATED`、`full_direct_owner=NOT_RUN`，不冒充 Direct UDP 或 TCP 实际出口成功。
- H1688 单 SOURCE GUI/Go CLI 配置验收独立 PASS，H1686 原 DLL 缺失失败永久保留。上一批 main governance 因 H1686/H1688 混 SOURCE evidence refs 与 cursor hot context 超额而真实 FAIL；[修复 c9e91fc](https://github.com/lly8666/wbd-next/commit/c9e91fc2a22ca13a3dc11ac01552e9f27469229d) 对 `evidence_refs` 单 SOURCE 和 7 项 hot refs 做了收敛，Action [43244785508](https://github.com/lly8666/wbd-next/actions/runs/43244785508) Feature catalog/Governance 均 SUCCESS，不抹去旧失败。
- PLAN029 继续 **IN_PROGRESS**。原 Rust ingress 仅有纯分流单测，无 DNS53 dispatcher、selective FakeIP、物理 Direct TCP/UDP；no-WFP 四阶段仍 `assemblyOnly=true` 且 route partial-intent crash、legacy-owned WFP migration、实际 Ready/Stop 未验。先缩小内核注入缺失原因/验证 Windows 资格；**不因为 UDP 诊断失败即擅自并养两种 TCP 后端**。D1–D5/P1–P2、bounded flow padding 仍 NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1690 real signed Windows Wintun UDP control and TCP kernel SYNACK both failed despite native local listeners; preserve first packet failure and no-WFP no-Defender-edits scope."}
```
