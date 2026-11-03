# H1012｜PLAN028真实Go认证租约→Rust唯一owner源IP归属门

2026-11-03用户要求继续大胆施工。当前SOURCE `34f5c15` H1011证据已经真正证明一台设备Game2/4使用单服务端443、按五元组多个lane、坏lane1后其他lane真实UDP echo且Go TLS/Rust M4 owned Stop PASS。**本SOURCE修复下一处必须先解决的实际隔离缺口：旧自动租约只在Go冷控制/OS安装，Rust M4解密后直接向服务端TUN写完整IP，未校验包内源地址属于哪个已认证设备。共享TUN前不可留下该漏洞。**

这笔完整跨层源码接线：
- `admission_v4.go` 为服务端V4会话补`AuthenticatedLeaseIPv4`，独立核实真实TLS已认证的冻结租约；用户修改公开`Negotiated.Lease4`不能伪造Rust租约。
- `bridge_v4_embedded_linux.go` 将保护TLS回包中的服务器分配/32编码为4B本机私有 C 调用；仅真实Go server正常完成Rust `commit`且M4未启动时写入那个确切handle。不能从未认证outer tuple/NAT/IP或手动CLI覆写。失败必须按照原Stop/Abort流程撤销。
- `v4_embedded_go.rs`在每条原Go TLS生成的Rust Entry中保留一个无锁小型可信客户端源IP字段；`wbd_m0_embedded_go_bind_authenticated_client_ipv4`限server、ACTIVE、未绑定、未启动、未归Game组的精确generation，拒绝重复/不合法IPv4；Go Normal和Game调用方将其连接在真实Rust worker启动前。Native Game组在Join时要求2/4 lane的自动租约完全一致，不允许地址混组。
- `v4_session_address.rs`只有O(1) IPv4版本/IHL/源地址比较；Normal `ProtectedBackgroundRx.consume_original`、Game及Game+FEC完整批的Rust M4 TUN写入前检查真正AEAD/PN认证并重组后的IP。Game+FEC整批preflight，发现伪造源IP时没有部分TUN写入。无新的每包回执、稳态header、Go逐包搬运、全局锁、计时器或额外常驻worker。手动IP尚没有受保护的每client地址所有权传递，沿旧行为，不能冒称全部手动场景已隔离。
- 原Go真实TLS夹具增加服务器Lease4被调用方突变的拒绝用例；Rust纯IPv4源校验单测含设备隔离与损坏IHL。原Linux双netns夹具新增`WBD_V4_PUBLIC_AUTO_IP=1`：真正客户端安装/复用受保护TLS租约随机/32、内核iproute读回，原Rust owner UDP应用回显、真实Stop。CI在同一源构建/二进制下复用一次该原native场景，不增加新造传输协议或手写合成PASSED。

**当前资格严格限于后续Actions真实结果**：此提交未测试前为`IMPLEMENTED_NOT_TESTED`；新auto-IP native若失败按日志明确定位修复，不用原H1011手动Game OFF PASS替代。仅一设备一session的Rust源地址绑定不能代表同账号2设备并发TUN分发完成，仍须一个Rust TUN reader+按目的/32 O(1)出站路由，并统一server五元组按客户端Cold加入。Rust目前没有共享TUN单reader，不启动生产A+B。Linux/Windows原生网络变更通知、7模式交接、Game4FEC最高、真实H998 1500→1280缩窄FAIL均保留未宣称通过。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient","game-lanes"],"reason":"Original Go protected per-device lease now binds native Rust server owner and verifies Normal, Game and FEC reconstructed IP before real TUN write; exact auto-IP OS netns Action added, true multi-client still unimplemented."}
```
