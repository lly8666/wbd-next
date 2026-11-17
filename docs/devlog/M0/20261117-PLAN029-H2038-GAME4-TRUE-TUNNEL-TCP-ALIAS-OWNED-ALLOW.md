# PLAN029 H2038｜Game4 CN 真 Tunnel TCP 反向失败：已有测试 owned Defender 远端源选择漏 Game4

- 最新 H2037 SOURCE `99a621ca919183f8ed228feb1f2fd981be895892` [原生 Action43913748050](https://github.com/lly8666/wbd-next/actions/runs/43913748050) **FAIL**，但原 Windows/Linux Rust组件、Go产物编译 **PASS**，真 Game4四 TLS lane、原Wintun、CN DNS→FakeIP、物理Direct UDP与32KiB TCP/FIN、Tunnel UDP 已返回原应用回执。**不能据此宣称Game4整体PASS或Stop合格**。
- **第一真实业务失败**：普通Tunnel双向TCP45902，Windows客户端→Linux server真实echo通过，Linux客户端源 `203.0.113.77` →Windows监听`10.66.0.2:45902`连接超时；Windows `server_received=0`、Linux `client_echo=false`。原测试 `.github/workflows/m0-wl-public-normal-full.yml` 的精确 owned Windows Defender Allow 的 `$tcpRemote` 只在Normal Direct / H1937 P1 ABBA时选 `203.0.113.77`，Game4 CN场景仍选 **`10.66.0.1`**，与真实 Linux source不符。历史H1936出现相同旧远端ACL问题。该证据高度支持入口阻挡，尚未同源重测证实单一根因。
- H2038 **只修改原真验收环境的现有owned单规则选择**，在 `WBD_PLAN029_GAME4_CN_SCENE=='1'` 时选确定的 `203.0.113.77`。仍仅 `TCP`、`LocalAddress=10.66.0.2`、`LocalPort=45902`、`RemoteAddress=203.0.113.77`，原readback/Stop/finally精确删除不放松；不加新规则、不关防火墙、不恢复WFP guard、不改变Rust/Go产品数据面。H1934静态测试新增Game4条件断言。
- 本来源新原生四lane签名场景网络/双 Stop **NOT_RUN**；不复活共享CDN同IP双域名专项（用户标为NOT_REQUIRED），不重跑已归档的 H2031/H2036填充（20..30条/2..3s、0..500B/MTU、无累计预算，原pcap/业务/Stop PASS_SCOPED）。
- H2037同SOURCE治理及feature job另有 **`evidence is for a different SOURCE`**（G2校验），与产品入口失败分离；保留原失败、不以跳过检查洗绿。优先收H2038真实Game4反向TCP结果后定向处理治理源边界。

```feature-impact
{"kind":"none","ids":[],"reason":"H2038 corrects only the exact owned Windows TCP45902 test listener remote address in original Game4 CN real workload, not product behavior, while retaining hard source and Stop gates."}
```
