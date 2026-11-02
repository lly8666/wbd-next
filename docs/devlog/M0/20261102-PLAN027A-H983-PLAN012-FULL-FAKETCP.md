# PLAN027A H983｜全量双端真实数值收取与另一Linux装配遗漏修复

本轮先收集实际每条Actions而非只看绿色：
- Windows/WSL2 同一预构建source `b9966eec...`：[#41496471520](https://github.com/lly8666/wbd-next/actions/runs/41496471520) Fixed1460 Windows/Linux 1375/1375；[#41496482942](https://github.com/lly8666/wbd-next/actions/runs/41496482942) Fixed1500 1415/1415；[#41496496092](https://github.com/lly8666/wbd-next/actions/runs/41496496092) Normal1460 1389/1389（Windows SYN、Linux SYNACK MSS均1420，物理各1500）；[#41496509099](https://github.com/lly8666/wbd-next/actions/runs/41496509099) Auto1460 1375/1375；[#41496520728](https://github.com/lly8666/wbd-next/actions/runs/41496520728) Game4FEC1460 1358/1358。全部真 Go TLS / Wintun + Linux TUN 双向UDP/TCP / Stop PASS；没有重跑。
- 当前Linux-only product source `d83159adf97256d4ce4983d8a95e8198cb0bdc72` [#41496813152](https://github.com/lly8666/wbd-next/actions/runs/41496813152)：独立原Go client+server真实AF_PACKET/TUN、Rust、双向业务和Stop **五场景PASS**。Normal1460→双端 MSS1420(实际TCP option `0204058c`)、wire1420、TUN1389；Fixed/Auto1460 MSS1420 wire1420 TUN1375；Fixed1500 MSS1460 option`020405b4` wire1460 TUN1415；真实非对称 Fixed client1500/server1280 MSS1460/`1240` option`020405b4`/`020404d8`、wire1240，双端 OS TUN1195，有实际server外层1280限制；**不强抬高**。所有初始、认证及OS后回执有来源，核验脚本逐字节检查。

另一个 PLAN012 同一正式产品的Linux **combined原生 [#41496813024](https://github.com/lly8666/wbd-next/actions/runs/41496813024) FAIL**：首错 `original current V4 SYN MSS actual bytes inconsistent`。不是Rust预算错误：它只把 `public_v4_mss.go` 复制到原Go checkout，忘记一起安装含真实SYN/SYN-ACK构造、验字节、重传冻结的`packet.go`、`client_association.go`、`association.go`、`association_test.go`与公共字节测试，底层仍发送1360，Rust预算1420，真Go出站门正确拒绝。此次把其独立构建入口合并到**既有唯一H970装配清单** `tools/m0_install_public_faketcp.py`；七个文件全部双SHA确认以后一次性装配，紧接 `go test ./internal/faketcp`。不新增legacy分支、不动生产预算，不触碰现有已合格程序和原失败。下一次PLAN012真实结果仍待Actions。

```feature-impact
{"kind":"none","ids":[],"reason":"H983 only corrects an independent Linux CI original-Go assembly that retained old SYN MSS bytes; records source-scoped already proven current product results, no product code or feature-card status promotion."}
```
