# PLAN028 H1064｜Linux Game 原生切网复用 Normal 的会话 supervisor

根因：原 `r0/go_overlay/internal/v4productcli/linux.go` 的 Game2/4 分支在一次 `runGame` 结束即返回，不订阅 Normal 已有的 `watchOriginalLinuxUnderlay` 原生 rtnetlink 200ms/500ms 物理网卡/源IPv4变化，更不重认证真实 TLS/Rust Game group。不能把 H1046 七模式启动和 H1052 账号隔离的 PASS 推广成 Game 真实切网 PASS。

本包唯一改动边界：将 **client auto-IP Game2/Game4** 接入既有 `runOriginalLinuxClientPaths` 控制器，复用原 Go/TLS、Rust M4、Game/Record/FEC/AEAD/PN、1–30s 原有 retry；同一主进程 TUN 在所有 generation 期间保持打开。新 Game generation 旋转**客户端源端口组**，服务端目的端口仍为443。原 Rust Game 客户端还没有能让两组同时争用同一 TUN 的 client shared-reader/fanout；因此本阶段**不冒称 A→A+B→B Game overlap**，严格按“发现新物理出口→取消并 join 旧 Game owner/Raw/TUN 借用→新 TLS 账号认证/租约校验/MTU readback→Game M4→新业务”的已断直接恢复路径，不让两个 M4 worker 抢读 TUN。只有完整旧 Stop 返回才开启下一组；Stop/user cancel 不复活旧实例。

业务前 MTU 必须用实际新出口物理限制（外层用户意图普通默认1460B、不含 L2，实际缩至1280B）、原 Rust预算算/应用/读回内层；同安装新原生 TLS 租约必须保持旧合法 /32，不因临时断链误改 TCP 所见地址。客户端 Game 加可选真实 M4 READY 事件，原 Game 手动路径保持原有；GAME4 copy schedule 异常也必须执行 owned Stop。非 FEC tag 保留明确拒绝 Game 的 stub，不会回退 Go 假热泵。

**冻结 SOURCE x86 Linux 原生完整工作包**：一起修改 client+server 已有调用接口、原 Rust group 一端资源 owner、原始 fixture `tools/m0-v4-public-real-linux-netns.sh` 和单元港口组检查。在当前 `m0-plan012-combined-functional.yml` **同一 SOURCE 构建**后增一个真实 Linux/x86_64 两端 Game4 fixed6 样本：原 Go TLS/4个独立FakeTCP lane/同一服务端443/真实 Rust FEC、client真实 10.25.0.2→10.25.0.3 路由源IPv4 change + 外层物理 MTU1500→1280，必须证旧组 Stop→新组认证+Rust M4、同安装 /32 不变、新内层MTUOS读回和5个真实 UDP echo。此时仅 SOURCE_CANDIDATE，不能先宣称 native PASS；原 Normal 多会话和七模式启动旧有效结果按原 source 保留。

平台轮换按用户 2026-11-04 最新规定：**本 Linux 任务 x86_64 client + x86_64 server**。下一完整 Linux 测试任务必须 ARM64 client + ARM64 server，Windows 不算轮换。不是异构混接，不重复 H1053–1055 QEMU 工位。H998在线收窄FAIL、旧 ARM64 Game4FEC Action FAIL、远端ICMP未测、CPU/p99未证和Windows物理切网NOT_RUN保持不变。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1064 original Linux Game2/4 auto-IP joins existing rtnetlink native path supervisor with exact old Game M4 Stop and generation ports before new TLS/MTU; source-locked Game4 FEC6 true x86/x86 path switch native fixture pending."}
```
