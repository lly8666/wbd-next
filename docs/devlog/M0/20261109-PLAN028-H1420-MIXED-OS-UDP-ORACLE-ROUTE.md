# PLAN028 H1420 | 已真实双认证，修单个测试中的路由/回执歧义

[H1419 Action42497568069](https://github.com/lly8666/wbd-next/actions/runs/42497568069) SOURCE 8be186b3cca1ed65ae5e4054c652109da9c090d1：原 Windows 单签名 Npcap/Wintun Alice + 独立 Linux netns Bob + 单 Go TLS443/Rust 共享 TUN server；原服务器 active_detached_flows=1→2，Bob 原 client Go TLS/Rust M4 READY；从双端真实 UDP 回显判据失败，TCP、A Stop B 存活尚未触发。原失败保留；Windows WAL 无残留、namespace bridge/IP/原默认路由精确恢复。

全链路两处夹具干扰：Linux Bob 手工 10.66.0.3/32 TUN 没有服务端内层 10.66.0.1 的 kernel 路由。仅在其真正受保护认证和 OS TUN /32 读回后，在 Bob 自有 namespace 增加 10.66.0.1/32 dev wbdl1415 并读回 route-get，绝不触碰 Windows 或全局路由。旧 UDP app 同时接收服务端独立10Hz reverse 与延迟 echo，却只把本轮刚发的包算 echo；非VPN loopback 3秒50次只计入2次，观测到上一轮真实echo被忽略。修为真内核 socket 按原 payload 序号去重归因，同时单列 reverse_received，单轮至多32个/45ms drain；两个客户端各至少8真实 echo+5独立 reverse 才算双向 UDP PASS，不能仅绿流程。增加失败时6行内真实 app stdout摘要/计数。并将服务器 Stop 断言对齐真正存在的 V4_PUBLIC_SHARED_TUN_STOP_DRAINED role=server。

此批只修改本单一 native 原测试夹具；不改产品 Go TLS、record、Rust、FEC、ISA-L、MTU 默认或外层报文。新 Action 完全执行后按证据裁定，当前仍 NOT_RUN。

```feature-impact
{"kind":"none","ids":[],"reason":"One PLAN028 cross-OS integration fixture: owned netns inner host route, correct asynchronous echo/reverse oracle, and existing server Stop receipt; no product changes."}
```
