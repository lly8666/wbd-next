# PLAN027A H982｜Windows五个同源场景已派发；Linux原生首SYN冷竞态修复

真实H980 Windows/WSL2已有唯一源 `b9966eecb3e30820d298ff8b2fc5d069f10b9aad` Windows Go+Rust DLL/Linux Go+Rust编译、七模式legacy1400原生和Windows WAL [41494436902](https://github.com/lly8666/wbd-next/actions/runs/41494436902)、[41494436971](https://github.com/lly8666/wbd-next/actions/runs/41494436971) 全部SUCCESS。此为baseline非Fixed1460资格。

H981独立五个对同一H980预编译Windows/Linux二进制的场景已实派：Fixed1460 `41496471520`、Fixed1500 `41496482942`、Normal1460 `41496496092`、Auto1460 `41496509099`、Game4FEC1460 `41496520728`。各自实际业务、两OS MTU、handshake TCP option MSS、peer/record/Stop等结果**仍未收集，不预填PASS**。不会因本次H982新的Linux源码反向提升旧二进制SOURCE。

另一独立[H981 Linux ARM64运行41494964168](https://github.com/lly8666/wbd-next/actions/runs/41494964168)真的首个Normal1460双netns在20s时FAIL：真实两网卡1500，双方原始TUN预算1389，原Go Linux客户端**真的发出 SYN MSS1420，tcp_option 0204058c**，但原Go服务端尚未看到SYN；脚本等到server TUN接口就启动客户端，未等真实Raw AF_PACKET监听点；且原Linux初始建链只`WaitEstablished`不驱动原`EmitRetransmitDue`，虽重新认证路径有旧有界RTO。两个短缺放大冷启动竞态，不是数值MTU PASS。H982给原Go Linux一条实际raw bound低频标记，脚本在client SYN前等标记；首代和重新认证都使用同一原始有界 MaxSYNRetries，同一association冻结MSS，不增加新超时/协议或回退。重编仅必要的新Linux ARM64 CPU程序一次，复用连测Normal1460/Fixed1460/Auto1460/Fixed1500/Fixed client1500 server1280五真 netns，逐场实际SYN/SYNACK wire、peerMSS、record、OS MTU、DF、Stop。

同时修H981治理文件超过8KiB `41494964163`：缩短cursor汇总，所有历史细节仍在既有历史commit/evidence/devlog，不遮蔽FAIL。此提交只影响Linux产品与ARM64夹具，不启动第二次Windows构建。**默认1460，1500仅显式最大**。

```feature-impact
{"kind":"none","ids":[],"reason":"Linux initial cold SYN bounded retry and authentic AF_PACKET readiness test barrier, restore cursor governance bound; H980 Windows Fixed source and prior native results unchanged."}
```
