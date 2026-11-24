# B87｜冷套件真实通过；补原生 preauth 夹具

B86a SOURCE `15f2969f89e72f9573243e0122f68bb5ced43ac5` [Action 45381240919](https://github.com/lly8666/wbd-next/actions/runs/45381240919) **11 SUCCESS / 2 FAILURE / 4 SKIPPED**；双ABI、正式ARM64签名APK及完整Host源码门、两Linux oracle、功能目录和维护均PASS。正式APK [14912914468](https://github.com/lly8666/wbd-next/actions/runs/45381240919/artifacts/14912914468)。Android16 KSU实际综合冷套件 [14914477279](https://github.com/lly8666/wbd-next/actions/runs/45381240919/artifacts/14914477279) 的 receipt.json 实证：普通App→KSU su、x86原Go help、实际PhysicalNetwork、ART七类生产helper、四页和四种分流接管UI、ARM64转译原Rust MTU 1389/1375/1373/1358、原Go c-shared help均PASS；不是正式ARM64 ELF或业务E2E。

D2 [14914492915](https://github.com/lly8666/wbd-next/actions/runs/45381240919/artifacts/14914492915) 实际启动原Linux server、普通App→su、Network读回、真实RootService START，随后日志 NETWORK_SCOPE_VERIFIED → START_REFUSED，未启动原Go。对照生产Activity和Service，CI Activity设置 has_ca=true 却遗漏 tls_verify_server=true，触发既有CA配置拒绝；B87只修CI参数与正式App一致，不改变证书默认/原协议/生产热路径。Cuttlefish host Job在下载APK后旧路径缺少SOURCE失败，修到真实 artifact 的 android-root-app 子目录；仅host准入，不启动guest、不宣称KVM可用。B87用 [android-guest-retry] 只补D2 preauth与原标准Job，不重跑已通过的综合冷套件、API35/36或14个Linux弱网场景。D2即使成功也只到原Go TUN/RAW/SYN阶段，不重开已知SLIRP/TAP握手阻塞。ARM64实体业务/性能仍NOT_RUN，main不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Record actual B86a combined Android cold suite pass, fix CI-only CA/verification argument pairing and ARM64 admission artifact path; retry only remaining preauth and standard jobs."}
```
