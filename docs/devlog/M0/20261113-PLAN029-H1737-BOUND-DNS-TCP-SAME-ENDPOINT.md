# PLAN029 H1737｜Direct DNS UDP截断后同endpoint TCP/53物理非阻塞回退

- H1736 `d38bf1ccc6be7ac1954100c583d36d03b2fd8a61` 原 Go source [Action43404251080](https://github.com/lly8666/wbd-next/actions/runs/43404251080)、原Windows WinForms当前Go/Rust [Action43404251072](https://github.com/lly8666/wbd-next/actions/runs/43404251072)、治理 [43404250899](https://github.com/lly8666/wbd-next/actions/runs/43404250899) **SUCCESS_SCOPED**，CI-only原认证V3入口能编译但无真实029网络场景。
- 真Rust NativeOwner的Direct DNS收到UDP TC标志时，原DnsPending保留原问题/方向/ID/客户端队列，**只对同一个`dns.direct`:53**建源IP+IP_UNICAST_IF绑定的`PhysicalTcpSocket`、零等待连接检查、DNS-over-TCP 2字节长度帧，按原实际5秒deadline单轮最多16请求/每请求一读一写，最大2020字节；不向Tunnel DNS/系统DNS/其他IPv4回退。TCP回包仍过`DnsPending.accept`原名称与ID/CNAME/A严格校验，FakeIP仍需journal批量持久后才公开，最后由原Rust RX独占Wintun反向回包。
- 严格发送/接收分段、超长、0长度、异常/拒绝连接用例；`TcpDnsFallback`不新建每query线程，断开或超时仅给本ticket SERVFAIL并释放其资源。无新TUN reader、无Go每包调用、无Wintun loan在socket或文件IO期间保留。新SOURCE Windows/Linux测试待回收，历史失败保持。
- 真029 D1-D5/P1-P2、Direct kernel TCP/Defender owned和OS Stop、完整geosite规则、GUI live/性能和startup padding仍NOT_RUN，严禁用本批pure测试放行公共V3。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Add bounded nonblocking TCP/53 to the same physical dns.direct endpoint after a validated UDP TC reply, with one pending ticket and no cross-lane fallback; new-source native tests pending"}
```
