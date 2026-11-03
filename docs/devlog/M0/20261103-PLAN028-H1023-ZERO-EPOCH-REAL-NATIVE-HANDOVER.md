# H1023｜PLAN028：真正原Go零epoch设备接管→共享Rust owner交接与另一账号连续业务

## 已验真的来源（不得跨SOURCE晋升）

H1022 SOURCE `9d5eaf8f2c7f19fa79783d11ee924ed14f417720`，原生 Linux Action `41589306085` / job `125762078930` **SUCCESS**。三真实netns两个不同账号，一个server443，一个Rust共享TUN reader，原Go保护TLS自动分配两个不同/32。A5→A+B各12→停A后B5，真正UDP **34/34**，Rust kernel reader `routed=34 unrouted=0 backpressure=0` 且所有Stop/join，OS lease读回合格。同一原生二进制 1% netem 512 offered / 510 delivered / 2 missing；Fixed、Auto FEC短首包各64、Game2/Game4 native受限回归通过。证据：[H1022锁源](../evidence/M0/PLAN028-H1022-SOURCE9D5-REAL-TWO-ACCOUNTS-SHARED-TUN-20261103.json)。上述是**不同账号**并发实证，未声称同一安装ID交接。

## H1023需要解决的真实首要障碍

现有 Linux `runClient` 的新原Go TLS连接按协议发送 `V4Extension.Epoch==0`（客户端无法知道服务端秘密epoch）。`V4EpochStore.prepare` 旧逻辑 `newTunnel := want==zero` 在原活跃owner未退出时始终拒绝，故即使新网络已经可用、原TLS验证真实账号和自动InstallationID，**A→A+B→B在保护TLS阶段必失败**。纯粹扩大cBPF五元组或者Rust共享TUN不能解决这处逻辑owner障碍。

本次按原架构作最小真实改动：

1. `r0/go_overlay/internal/realityfront/admission_v4.go`：当且仅当原Go TLS已通过账号凭据校验、已有同一username+16B TunnelID对应逻辑epoch且同lane**恰好一个活跃incarnation**、服务端单独授予 `AllowLaneReplacement` 时，新的**零epoch**保护TLS连接可预留第二个实例；返回**原有逻辑epoch**，同时从crypto/RNG分配全新nonce，通过原TLS exporter推导新AEAD双向密钥。两个活跃实例、一个正在pending时第三个必须被拒绝。既有传显式旧epoch的Game加入协议和默认不开重叠的客户保持原合同。
2. `bridge_v4_linux_server_product.go`仅透传服务端冷授权到原`EstablishServerV4`；`v4productcli/linux.go`仅在真正已启用原Go受保护自动分配/32的并发server manager打开该选项。手动IP、匿名源IP、仅账号/公开InstallationID、默认API都不能自行请求夺取。
3. 保留原Rust共享TUN `SharedTunRoute` atomic alive fence，只有新TLS认证完成且新Rust worker起好才将/32路由从A切换给B，旧A归属于精确incarnation的`V4LinuxServerProduct.Close→ReleaseLaneInstance`，不会删除B或Bob。无新加密算法、稳态header/Go热路径数据复制和第二recovery控制器。
4. 原真实protected Go TLS测试 `TestR0V4PLAN028ZeroEpochAuthenticatedSameInstallOverlapAndSiblingIsolation`：无server opt-in时拒绝、same-install A/B零epoch成功且双向密钥+incarnation更新、第三个拒绝、旧A重复Stop拒绝并不能动B、其他安装仍活；返回B后还允许新C，最终所有epoch干净释放。原Action以实际Go测试包执行，无手工协议模拟。
5. 原 `tools/m0-plan028-two-client-real-linux-netns.sh` **延长同一已合格场景**（仍同一源码构建、同一server443和Rust共享TUN）：真实第四Linux netns中的 Alice 连接R，拿**原A同一个InstallationID文件**和另一个underlay端口；A在新TLS前确实还活着，R经原真实Go protected TLS获取同一 `/32`，server必须记录 `reason=same-lease-new-generation` 的旧A原Rust Stop。R应用UDP 6与独立Bob业务UDP 6并发，A及R两个client都原生Stop后，Bob再送5。总预期实际TUN回程`routed>=46`，这不借用先前34包PASS。仍保留每个账户隔离、严格OS/Stop/readback、Game2/4/FEC/1%回归及最终强制门禁。
6. H1022新源锁证据写入特性卡与本workstream cursor；新 H1023 SOURCE 没有自己的原生Actions结果之前标记`IMPLEMENTED_NOT_TESTED`。

## 限域与下一步

本轮完成以前不可冒称同安装交接PASS；即使真实netns通过，这仍只覆盖 **Normal/off、已有可用新underlay、服务端与客户端重建TLS**。Windows/Linux原生网络通知、200/500ms事件风暴合并、新出口数值endpoint重新绑定、per-device配置全七模式最高FEC、同账号两安装ID+另一账号同场、真实CPU/p99长期测试与 H998 物理MTU 1500→1280及ARM64 Game4FEC FAIL 均保留，不以这轮低损第一回显抵消。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient","idle-rotation-keepalive"],"reason":"Authenticated zero-epoch cold same-device lane handoff reuses logical session epoch with fresh original TLS/Rust incarnation and exact Stop, extends one-build real multi-account native source test to old-A+new-A overlap while Bob continuously sends genuine UDP. H1022 two-account result recorded; H1023 pending exact SOURCE."}
```
