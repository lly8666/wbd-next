# PLAN029 H2010｜签名 Windows/WSL2 同一个海外 CDN IP 双域名反向出口

- H1960原 H1958 Action43792684618只验证不同海外IP的CN FakeIP Direct / 非CN Tunnel及非CN→CN IP的业务Direct；不能证明同一共享IP的CN/非CN隔离。H1795 Action43556105215 独立真TCP53双endpoint及Stop PASS。
- 本SOURCE一 Action 串行复用原 CN Normal Wintun/TLS/Windows+Linux NPF/Rust 单owner、DNS/UDP/DirectTCP、Tunnel UDP/TCP、TCP53和黑洞 no cross fallback 基础验收；额外只测 **同一 A=203.0.113.77** 由物理 `dns.direct` 回复 `cdn.cn.example`、Tunnel `1.1.1.1` 回复 `edge.globalx.example`。原Windows app按展示8.8.8.8查询，CN需收到持久本地198.18 FakeIP，非CN必须保留原A。
- Windows两个原应用socket均显式选Wintun `IP_UNICAST_IF`，业务分别发到FakeIP:46131和真实相同A:46132。原WSL2上同一A作为原wbdwl4已owned /32并短期增加eth0 /32、Windows真实物理 /32 route，只此SOURCE写INTENT/核验OWNED/精确CAS清理。Linux两独立 UDP kernel listener以 **IP_PKTINFO** 验物理eth0与真实wbdwl4独立ifindex、原 underlay host source/lease source和逐字节回包。不能靠classifier-only或只比较本地地址伪造两个出口。
- TCP53、黑洞不回退由现有同一签名完整场景验证，固定普通Normal（无bulk、资源压力或重刷矩阵）。任何别名部分Apply失败保留第一异常，原finally删除本SOURCE确定资源；真实双Stop签收前 report保持NOT_RUN。
- Bootstrap冷源沿历史已验真实 Windows 原Go `faketcp/native_dns_bootstrap_windows_test.go` 的物理DNS帧/CNAME及本地 `windowsclient/native_bootstrap_dns_windows_test.go` 必填单direct拒不安全DNS；**本次没有真实接管后的新连接/唤醒 bootstrap 证明**，仍另项OPEN。Game4 CN产品Go当前显式冷拒绝，不把普通Game4通过计为CN分流。
```feature-impact
{"kind":"none","ids":[],"reason":"H2010 adds one bounded signed same-overseas-CDN A opposite physical/Tunnel egress fixture to existing original CN DNS/TCP53 blackhole/Stop native Action; product code unchanged."}
```
