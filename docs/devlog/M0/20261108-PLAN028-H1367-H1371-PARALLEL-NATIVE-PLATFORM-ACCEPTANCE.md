# PLAN028 H1367–H1371｜并行原生业务验收与外部误报分账

2026-11-08 同时启动 Linux x86 L0、ARM64 Game4 双向100%真实 OS 断网五用户、Windows 两张独立签名 Wintun 真内核 UDP；不同独立 Actions/平台 Runner，不把 ARM24e/x866c5/Windows 旧 M4 原包视作一个同源产物。

## H1367｜Linux x86 L0

- [原始 Action 42450177765](https://github.com/lly8666/wbd-next/actions/runs/42450177765) SUCCESS。真原 Go/Rust cgo 两标签测试 `TestPLAN028Game4ProtectedEpochZeroWholeGroupVsSingleLane` 原始日志 `--- PASS`，审计原归档 2 个文件 CRC PASS，ZIP SHA256 `5e09cf8ad1c5d01bd1737dd0e7b86749115e0a315991c4344d09a9c1543e72ac`。本场仅 tagged L0 boundary，不把 unit PASS 冒充在线 UDP/TCP 或完整 Game4 业务。
- 验收档案：docs/evidence/M0/PLAN028-H1367-LINUX-L0-SOURCEA4BF-GAME4-PROTECTED-ZERO-EPOCH-SCOPED-PASS-20261108.json

## H1368 + H1371｜ARM64 Game4 真实相关性断网

- [H1368 原始 Action 42450177745](https://github.com/lly8666/wbd-next/actions/runs/42450177745) 中 5 原始 Go TLS443/Rust M4 已认证租约真实在 Linux ARM netns/TUN 运行180秒并完成 5 客户端及 server Stop。真实 Game4 四lane **共用一条** veth 底层上下行同时100%丢包 **8.0177秒**，原始内核 qdisc 丢包上行**26,062** / 下行**26,108**，而不是虚构的 App 黑洞。
- Dave Game4 从撤损到原生 UDP 第一收件分别上行**136ms**/下行**146ms**。Alice/Bob/Carol/Erin 八个方向黑洞期真实业务交付比约 99.77%–100.05%，无新增连续无接收空洞；每个业务 19001 个原10ms bin 含尾段，五客户端 app error0、capacity flag0，server 所有租约 TUN queue overflow0、精确 Stop 完成。业务场景产品 **PASS_SCOPED**。
- 原 H1368 CI FAIL 是把 x86 审计器的 `len(bin)==18000` 误用于 ARM 原19001 bin；上传glob漏了 `h1353-physical-game4-blackhole.json`，但原 `h1368-native-game4-correlated-traffic.log` 实际打印的 qdisc start/restore ticks 和 drops + `h1250-qdisc-after.txt` 保留真实 OS 物证。[H1371 独立离线 Action 42450749950](https://github.com/lly8666/wbd-next/actions/runs/42450749950) SUCCESS，没有跑新的网络；原37文件 ZIP SHA256 `40479161b98ccc6a2363cf7d1a63db9b593a710065fcccd05785d0978a4b78ab` CRC PASS、离线2文件 ZIP SHA256 `af1866c8bdd106737964a538773dbd240f0e211ed93030c2353b2bfc23553750` CRC PASS。
- 原通用 rapid 报告原7 alerts 保留：五条 `ROTATION_CONTINUITY_NOT_PROVEN` 是此场特意把轮换timer停在600秒（运行180秒，未触发）；两条8010ms连续无收件是**事先安排的100%底层真实黑洞**。不能用这七个预期/未触发结果抹杀已经完成的真实业务；同样本场**不**证明轮换，由 H1363 真两轮 owner 交接另证。
- 验收档案：docs/evidence/M0/PLAN028-H1368-H1371-ARM64-SOURCE24E1-CORRELATED-GAME4-BLACKHOLE-PASS-20261108.json

## H1369 + H1370｜Windows 两张真实签名 Wintun 设备隔离

- [H1369 原始 Windows Action 42450303401](https://github.com/lly8666/wbd-next/actions/runs/42450303401) 使用官方签名 Wintun、同一 Windows 进程创建两张不同 GUID/LUID/ifindex/Alias 的真实设备，各有 Windows UDP Socket。A/B 真 kernel/Win32 UDP app 成功，精确 Stop A 后 B 仍继续真 UDP，B 的 Win32 socket 反向数据进入 B 的 Wintun native ring；随后 B 精确 Stop，旧代写入均被拒。原 Go Test **PASS (13.69s)**。
- 原 Action CI FAIL 是 **测试完成后**复制的 PLAN020 报告器查找不存在的 `r['result']`（H1369 实际正确定义 `r['classification']`），并让旧 source.json 的重命名日志布尔位变成 false。[H1370 原始四文件独立离线复核 Action 42450547596](https://github.com/lly8666/wbd-next/actions/runs/42450547596) SUCCESS，不重跑 Windows。H1369 原 ZIP SHA256 `0f3fe5b44e22830b67426ea3c7d7a22c32f0c29385991ecaa9c804b1d3c6b425` CRC 4 PASS；H1370 ZIP SHA256 `cacd0fd9c6b62040e0c62cec01003868daeb3d93421a081e9ddb1a3b1cd2b920` CRC2 PASS。
- 这是**真 Windows 双签名 Wintun native OS 驱动隔离 PASS**，但**没有**同时两个 Go TLS/Rust M4 原产品客户端在一个443服务端的双账号/双身份认证；原 Npcap outer、global WFP/默认路由及 WinForms 也没在本场验证，不将局部 PASS 扩展。
- 验收档案：docs/evidence/M0/PLAN028-H1369-H1370-WINDOWS-SOURCE5B63-TWO-REAL-SIGNED-WINTUN-NATIVE-ISOLATION-PASS-20261108.json

## 后续硬门

Windows 两个真正独立**认证的产品设备**在同一个原始 Go TLS443/Rust 服务端同时在线并 A→A+B→B 隔离仍需要测试；H998 同socket热 MTU旧失败保持，L0其它 packet 边界/L2剩余以及 L3 两条1800秒仍未完成。PLAN028 仍 **IN_PROGRESS**。原始 CI FAIL 不删除，真正用户业务成功的场景按其已经完成的范围为 PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"Independent test-only native Windows driver proof, existing original Linux boundary and ARM fixture; raw CI external auditor failures replayed strictly offline. No runtime product behavior or public feature changed and no feature card modified."}
```
