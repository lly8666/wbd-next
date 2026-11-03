# H1034 PLAN028 | 两秒只检查物理网卡和接口 IPv4

按用户最新要求，Windows/Linux 统一为每 2 秒读取一次到服务器的真实物理出口，重连触发只比较网卡标识与所选源 IPv4。
取消 Windows NotifyRouteChange2/NotifyUnicastIpAddressChange 与 Linux netlink 路由/地址/链路监听，不再做 200/500 ms 合并。
网关、路由及 MTU 变化本身不触发重认证；在网卡/IP 真正变化之后仍完整读取新路径 MTU，复用旧版 TLS 认证、MTU 预算/安装/读回和 Rust 精确 Stop。
网络暂时不存在时不触发假 READY；轮询继续等待，用户 Stop 立即取消。默认外层 1460 不变。
Windows 仍是 Stop→重认证，不能称为 A+B；Linux 仍复用当前真实 A→A+B→B。

针对性 Go 单元覆盖两秒周期和网卡/IP 差异，Linux 实际 netns 场景对应改为诚实的“2 秒轮询”标记；新 SOURCE CI 待完成。

## H1034 scoped tests

Source `ce9c128e712024164e586e89a76b395579370e78`: original Linux native [Action 41623425219](https://github.com/lly8666/wbd-next/actions/runs/41623425219) SUCCESS, including actual 2-second NIC/IP-triggered netns A→A+B→B and precise Stop. Windows Go production and test compile plus focused interface/IP cases: [preflight job 125874909144](https://github.com/lly8666/wbd-next/actions/runs/41623425293/job/125874909144) SUCCESS. Real Windows physical switch NOT_RUN; 2 seconds is sampling, not full reconnection SLA.

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1034 user-directed simplification: Windows and Linux poll selected physical interface/source IPv4 every 2 seconds, no broader IP/route subscriptions; original authenticated reconnect unchanged."}
```
