# PLAN029 H1771｜前置门拦截旧cleanup字符串，独立旧Go ClientConfig RootCAs不匹配

- [H1770签名工作流43530167075](https://github.com/lly8666/wbd-next/actions/runs/43530167075)（SOURCE `69c55a0584bbf3703a2b61b75dcf64aa94b74bae`）**未执行**新D2 Windows↔Linux业务；单项`test_h1767_one_selected_dns_blackhole_no_direct_fallback`断言旧finally列表中`p029_dns_blackhole_guest,p029_dns_blackhole_win):`必须直接闭合。H1770合法追加`p029_d2_tun_guest,p029_d2_tun_win`，导致测试字符串匹配FAIL，非原生Wintun/UDP失败。H1771测试分别检查H1767 DNS和H1770 D2两个真实子进程组均由原finally收回，不依赖列表尾部，其他所有旧安全约束/实网门不放宽。
- 并行[H1770 Windows/Linux Rust组件43530167146](https://github.com/lly8666/wbd-next/actions/runs/43530167146)两端成功，新TCP53帧解析与已有原M1 AEAD padding源码测试PASS；[D3资源压力纯组件43530167175](https://github.com/lly8666/wbd-next/actions/runs/43530167175)的normal/kernel/engine/FEC/receipt全部PASS。仅纯组件/编译，D2实际流和DNS应用TCP53产品仍未RUN，P1/P2未测。
- 独立[原Windows owner ABI43530167292](https://github.com/lly8666/wbd-next/actions/runs/43530167292) 已越过长期H1766旧第一失败：`tls.go`精确固定原Go Git字节保留、**不覆盖**，Rust MSVC owner/Health/ABI+release DLL皆PASS；下一真实Go编译首错是`ClientConfig`固定原版无`RootCAs`字段，而新的`admission_v4_test.go`和`bridge_v4_windows_dual_test.go`硬构造该字段。维持原凭据TLS不可擅改的防护，此独立ABI红灯作为SOURCE契约迁移事项，不通过覆盖原TLS或跳过证书校验虚构绿灯。与PLAN029签名产品分流层独立。
- H1771一个SOURCE显式`[plan029-v3-real-direct-udp]`仅单Normal真实签名一次；H1769已证明D1物理DNS目标零回退和Stop PASS保留，不恢复028矩阵、不启动030。

```feature-impact
{"kind":"none","ids":[],"reason":"H1771 only corrects brittle existing test cleanup-list assertion and records independent original Go TLS RootCAs contract mismatch; H1770 product source and feature cards unchanged"}
```
