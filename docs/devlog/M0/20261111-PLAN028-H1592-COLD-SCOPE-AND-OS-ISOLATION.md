# PLAN028 M0 H1592｜接收真正Windows30%结果，修短场资格误标

2026-11-11；PLAN028 **IN_PROGRESS**。最新源 `fd4732ec4adffa442a0bc25a145ed6ea1d1259a8` 与旧 `dccf323b` / `c3e60772` 不混。

- 取回 Action [43009320538](https://github.com/lly8666/wbd-next/actions/runs/43009320538) 原始 artifact `13849694203`，读 `h1548-loss30-strict-native-report.json`、`h1548-windows-alice.log`、`windows-binary-manifest.json`，整场 **SUCCESS** 且**仅H1579冷建链硬门PASS_SCOPED**。物理双向损包30%、单程200ms，真实原Go RTO `copied=3 joined_before_Rust_M3=1`、凭据TLS及Rust M4、原Linux真kernel反向UDP、Windows签名Wintun手动`/32` 与派生1389 MTU OS读回、15/90/idle0和双端Stop／WSL/netem/WAL清理均有输出。逐平台原始编译hash、运行后端和限制写入 [H1592 evidence](../../evidence/M0/PLAN028-H1592-SOURCEFD473-WIN30-COLD-TLS-PASS-SCOPED-20261111.json)。原600s和30%业务流 **NOT_RUN**，不能因Action绿灯推广。
- 同源 `43009320451` 治理+feature catalog SUCCESS，`43009320389` Windows原Go签名WAL及Normal/Auto/Game2/4/Fixed scoped SUCCESS，`43009320436` Linux x86/ARM两账号手动/32真实原生 SUCCESS。旧 `42979705842` 五客户端150s overall FAIL但original后续源 `dd82db7e` 150s和Stop实际PASS_SCOPED；原始失败保留不重写。原 `43008382596` 仅预检旧manifest FAIL也保留。
- 读取新源小报告发现**真实治理/量测缺陷**：短H1579冷TLS `normal-report.json` 与 `report.json` 竟写 `qualification_scope:ORIGINAL_600S`，而相同原始严格报告明示 `600s_outer_capacity=NOT_RUN_H1579_SHORT_30PCT_COLD_TLS`。只修 `tools/m0_plan028_h1548_one_windows_four_linux_600.py` 该字段按`l1_150/h1579/probe/600s`明分，保持 `mode_public` 和真实产品/fixture包型不变；加强 `.github/workflows/m0-wl-public-normal-full.yml` H1589报告校验与 `tests/test_m0_plan028_h1579_win30_cold_auth_scope.py`。**不会为纯报告修复重跑已通过的30%冷链。**
- H1587 SOURCE`3b6d53c3`双Windows同机多实例中B的原Go TLS+Rust AEAD已经通过，但B的Windows route WAL严格CAS失败 `route is not owned; refuse to replace`，原证据 `43001721886` 保留FAIL。由原Go路由装配可见每个独立Wintun默认都请求同一服务端物理/32 escape和两条/1捕获，属于实际OS共享路由所有权冲突；粗暴删除A路由/忽略Guard会破坏A业务，不能用源码测试替代双真实签名OS。新的安全共享路由方案及真实B业务/A Stop是收口前硬门。
- H1592仅用一场后续当前SOURCE Windows自动AES256+四Linux三cipher 150s 标记做变更后代表业务回归。新SOURCE全套L2/1800s仍待做，旧ARM64长测可按未改范围复用。用户默认没有改变：外层1460、FEC Off、Linux rotate0、Windows15/90/idle0。

```feature-impact
{"kind":"none","reason":"H1592 only corrects the source-specific test report qualification scope, existing gate and M0 handoff/evidence; no product feature, protocol, default or GUI changed."}
```
