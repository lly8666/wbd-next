# PLAN029 H1724｜单Rust入口选择性FakeIP 动态映射接线

- 基准 `651bf5ce172ed12ddaa824f05f3f5cf220365c19` [H1723双OS Rust组件Action43390874112](https://github.com/lly8666/wbd-next/actions/runs/43390874112) Win/Linux **SUCCESS_SCOPED**，包括新DNS独立TTL/LRU纯逻辑，不等于DNS socket/产品出口。
- DNS经过真实网络解析时才可把已**写前持久化**的FakeIP→真实IP作为首个业务流查询；旧 `Arc<SplitPolicy>` immutable 映射没法让同代DNS公布新FakeIP，本批新增 `PacketIngress::on_ipv4_with_announced_fake` 仅第一次分类查询同代FakeAllocator整数键，活动flow沿固定pin，不更新/反查共享CDN真实IP。
- FakeIP在All/BypassLan绝不可变成Direct，未宣布/过期不可用、real落FakeIP池不可用；不更改普通Tunnel热路径、Wintun borrow或Rust native stop。新跨平台用例构造CN假地址→海外CDN Direct及同真实IP无假地址仍Tunnel，源码结果待同SOURCE CI。
- 当前产品原 Rust worker尚未接真实Direct TCP/UDP及强制双DNS/GUI Applied；D1–D5/P1–P2/Padding **NOT_RUN**。不重复诊断或启动030。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Expose durable generation-owned FakeIP lookup at first split flow without shared-CDN real-IP pollution; crossplatform native tests pending"}
```
