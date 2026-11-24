# B91｜真实 Android 内核、系统 DNS 与认证后七模式原 M4

B90 SOURCE `0d710fd6e39abb4d85c6935f56b09756d28c47ea` [Action 45409736062](https://github.com/lly8666/wbd-next/actions/runs/45409736062) 11 SUCCESS/1 FAILURE/5 SKIPPED；双 ABI、正式 APK [14928580697](https://github.com/lly8666/wbd-next/actions/runs/45409736062/artifacts/14928580697)、原 TLS/Rust Game Host cold oracle PASS。唯一 KSU job [138503568130](https://github.com/lly8666/wbd-next/actions/runs/45409736062/job/138503568130) 实际 boot、Root 授权及文件上传通过，在 mv/chmod 部署权限失败，专项均 NOT_RUN。B91复用已通过的 D1 root-owned cp staging，修正 fixture route-journal.json 文件名。

B91一次 KSU boot，逐场景独立记录：原 single/group/all UID+完整 CN FIB、普通 ART UDP↔真实 TUN fixture、原 Stop；原 Bionic 物理 DNS；真实 Android Network.getAllByName→原 system DNS RPDB/NAT/relay→物理 DNS 或隔离 TUN UDP DNS fixture、CN 自定义规则分流（官方规则 Host 历史独立）。测试 /32 不是认证租约。另用原 ClientAssociation 和原 ServerAssociation 双端真正生成 SYN/SYNACK、原 Go TLS+账户及原 lease registry，进程内冷 wire 交换，不写假 SYNACK/冷 bundle。原 Normal/Game 产品 Connect、原 TUN/MTU/lease/UID callbacks、实际 Bionic RAW 和 Rust native worker、Fixed/Auto pending/Game2/4 group、普通 UID 发包 native TX、原 joined Stop 和内核清理。七模式 postauth 与 B89 preauth 不同，不宣称物理 peer 或双向 M4 业务。失败只在内核清理未证明时阻断后续场景。无性能基准、无额外安全或产品热路径修改。新 SOURCE 全部待 CI；后续真实 RootService 网络切换/配置切换、最终 ARM64 peer E2E 尚未证明。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Record B90 real results and repair CI staging/journal fixture; actual Android kernel UDP roundtrip, system DNS routing, and original authenticated native Normal/Game postauth and Stop component tests."}
```
