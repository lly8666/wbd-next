# PLAN028 H1039 — Game 最后一组 Stop 后恢复原 TLS 端口过滤

H1038 service-side Game2/4 已可由 Rust 原有 Health90 Stop-bit 判死，随后只回收该账号组；但进一步检查发现长期复连黑洞：一个 `SO_ATTACH_FILTER` 持续过滤上一组的真实 TCP 四元组 DATA。如果最后一组已完成原生 Stop，下一位客户端/NAT 复用同一四元组，即使新 SYN 可见，新 TLS ClientHello 的 payload 仍会在 AF_PACKET 层被旧过滤器丢掉。

修复只在最后一个已认证 Game owner 成功完成 native Stop 且 `detached` 为空时，由原 Go FakeTCP endpoint 对同一个原生监听 socket 重新 `SO_ATTACH_FILTER` 原有 `rawReceivePortFilter(local,443)`。若还有 B、C 等已认证组，继续构造整组 union 过滤，不让他们的 Rust DATA 意外回流到 Go。无未认证 FIN/RST 清理权限；不重建 socket、不重写 TLS/AEAD/M4，不引入 Go DATA forwarding。

针对性 `TestPLAN028GameLastGroupRearmsOriginalTLSFourTuple` 在 Linux classic-BPF VM 验证同四元组：仍属 Game 原生时 payload 拦截；最后组 Stop 后原始 TLS 收包恢复；不相干目标端口继续拒绝。原 combined 流程会跑全部 faketcp Go 测试，并在同源码重跑真实 Game2+Game4 M4、两组 Game2 UDP 及 Stop。

上一源码 H1038 `f4c80344e2d91e968299d5855fccc43fabeb9988` 的 Linux 原生 Action [41638178918](https://github.com/lly8666/wbd-next/actions/runs/41638178918) SUCCESS，ABI Action [41638178980](https://github.com/lly8666/wbd-next/actions/runs/41638178980) SUCCESS；**仍不宣称真实 90 秒 Game 服务器自动退休已测试**。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1039 after last credential-authenticated Game M4 Stop, restore original kernel TLS bootstrap receive-port BPF so legitimate recycled NAT 4-tuples can reconnect while sibling Game groups remain excluded from Go."}
```
