# PLAN029B H2123｜首个原生三代GUI实测首代DNS失败，限域修夹具后只重跑一次

原 [Action44135197316](https://github.com/lly8666/wbd-next/actions/runs/44135197316) SOURCE `b1ab51be87c6d0c0aadd57283ac12da34ca238bf` 完整cheap/B4纯单测、WinGo/WinRust/LinuxRust、Linux原Go/Rust、Win原Go/Rust release和驱动签名全PASS；原生Win2025/WSL2 B4 **FAIL**，不是PASS。真实WinForms第一代 `WBD_WINDOWS_OS_APPLIED`、`WBD_WINDOWS_CLIENT_READY`、`PLAN029B_B4_REAL_GUI_GENERATION_APPLIED ordinal=1` 均真实到达；紧接原应用 `QueryA` 取得同票的非正响应：`PLAN029B_B4_FIRST_FAILURE IOException PLAN029B B4 real A CNAME/TTL answer absent or negative`。失败路径完整 `M0_PLAN027_NATIVE_STOP_RESULT stage=wal_kernel_crypto result=PASS`、`WBD_WINDOWS_NATIVE_DISCONNECTED_V1 wal_restored=1 rust_stopped=1`，Linux原M4 shared TUN Stop也完成。**首代业务出口/旧FakeIP以及后两代全NOT_RUN**，不能以单个Applied推B4成功。

下载原artifact `14352941680` ZIP SHA256 `d4ce8398baff7fc4fac7344759b1684adb2da6a1d23d661fb102995e294ff91b`，24成员CRC PASS，报告SOURCE、产品SOURCE、夹具SOURCE均相等b1ab；第一次原ZIP缺B4 guest bounded日志，未证明上游是否收到。回读原冷配置 `cn_domain_fakeip=true`、源物理DNS/隧道DNS独立，不改产品热数据面。失败场景独有两个接线缺口：原HyperV物理UDP53仅按H2050 bootstrap开放，B4未继承该受控规则；原普通双向UDP应用地址 `linux_app4` 对B4仍采用 `10.66.0.1`（CN模式是LAN Direct），实际日志反复WinSock 10051，而已存在的真正受保护测试公共TUN别名应为 `203.0.113.77/32`。本批只修这两个夹具条件，物理UDP53复用同一owner H2050原INTENT/OWNED和finally确权清理，只开放原Linux guest UDP53和单Win host来源，不重建物理全局规则；双向应用选择已有公共TUN alias，保留原路由/业务Stop。一次失败打印DNS rcode/ancount/长度、不含秘密，把B4 guest bounded日志纳入既有归档。补H2123廉价静态防漏门。

本次修复为**候选SOURCE**：新真实Win三代Action/已验哈希与Game2/Game4/B5同VM10Mbps CPU/实际GiB/RSS/p99仍NOT_RUN；旧b1ab原FAIL继续归档，下一次若同类错误无新信息只查第一个真实上游票，不刷seed。H2112 /128 IPv6限域PASS，B0–B3既有结果不重刷。029/029B仍OPEN，030未开。

```feature-impact
{"kind":"none","ids":[],"reason":"H2123 only tests/CI bounded physical DNS and original TUN alias fixtures, plus exact-source FAIL evidence/cursor; no product runtime or feature readiness promotion"}
```
