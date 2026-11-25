# B109｜独立原远端业务七模式并行，修正服务端验收分支

B108 SOURCE `6f63538348aabfeff6eaca39fac63cf53050b6be` [Action 45553595090](https://github.com/lly8666/wbd-next/actions/runs/45553595090) 11 SUCCESS / 2 FAIL / 8 SKIP。真实Android [139002080126](https://github.com/lly8666/wbd-next/actions/runs/45553595090/job/139002080126) veth/tc/ADB carrier kernel admission PASS，独立原Linux server真实SYNACK、Android真实authenticated lease OS readback、正式RootService native M4+UID READY 均有明确marker；两relay host tx15/rx18、guest tx18/rx15，共33个双向原报文。不是进程内TLS模拟。整job FAIL，server independent READY及普通App业务未证/NOT_RUN。原因：B108原脚本同时要求 Normal auto-lease shared-multi 的原RAW SYN/SYNACK marker和互斥singleton server READY。源码 runServer 在 leases!=nil 时进入 runSharedMultiServer，后者发布 V4_PUBLIC_MULTI_SESSION_READY，非 singleton marker；Game shared 模式又走 game_linux.go 原mixed group owner。B108未输出 server-stage-enums 文件内容到日志，故不倒推server端marker PASS。独立Linux carrier [139000254858](https://github.com/lly8666/wbd-next/actions/runs/45553595090/job/139000254858) 普通kernel TCP connect超时，失败保留，不能以Android AF_PACKET冷建链代替kernel TCP admission。

B109新SOURCE同一CI载体，七独立Android guest（max-parallel7），Normal/Fixed/Auto使用原Normal auto-lease multi-session server，Game2/4 off/fixed使用原shared mixed server，真正选中普通App UID。保留独立原客户端模式、SYNACK、认证租约、M4 READY检查，TLS测试CA验证全部开启（CI-only，不改变正式默认）。Normal三模式要求原server SYN/SYNACK+MULTI_SESSION_READY；Game四模式要求原server group READY及实际2/4各lane原protected TLS Rust M4 committed marker。两端原carrier TX/RX必须实际观察，server READY允许短暂等待异步发布，打印仅固定枚举。之后原普通App真实TCP/UDP 8+8、1MiB每方向逐字节校验，真实原Stop与内核readback。各mode独立artifact，任何阶段失败不以其他mode顶替。不改生产代码、protocol、MTU、FEC算法、热路径或正式证书策略。独立Linux kernel TCP admission继续原普通场景，补失败时tc/relay/socket kernel计数，非防御矩阵。不声明Linux carrier修复已成功。新SOURCE待CI。

远端E2E/真实FEC恢复/生产READY自动重连/实体热点及ARM64真机仍未证明；CI carrier含ADB TCP控制流，不能作为物理丢包/性能依据。main独立推进到 db83a2e6ac13，未改或合并。治理历史失败保留。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Record B108 authentic independent Android cold peer progress and failed gate; use exact multi-session/Game server receipts and seven independent remote business jobs."}
```
