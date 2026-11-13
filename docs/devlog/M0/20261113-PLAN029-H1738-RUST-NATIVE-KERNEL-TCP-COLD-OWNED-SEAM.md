# PLAN029 H1738｜原Rust NativeOwner内核TCP Direct双腿接线：先保持owned安全阀关闭

- H1737 SOURCE `dc7ced5647873190f493f7c0d7f132216ed10147` [Windows/Linux Rust组件43404944766](https://github.com/lly8666/wbd-next/actions/runs/43404944766)、[GNU cross ABI43404944742](https://github.com/lly8666/wbd-next/actions/runs/43404944742) **PASS_SCOPED**。历史PLAN013 [43404944781](https://github.com/lly8666/wbd-next/actions/runs/43404944781) 因旧M4装配不可有新增文件断言FAIL，与029原Rust数据面组件无关，保留不篡改。
- 本批Rust`NativeTcpActor`真正使用 Windows 内核listener / SYN-ACK/FIN/NAT，逐流物理`IP_UNICAST_IF`确认的非阻塞TCP，bounded 8 flow relay、256包原RX Wintun发送邮箱；仍是ONE original Rust TX/RX 和ONE Wintun，不引入Go逐包回调、无线程池或第二TCP栈。Direct-only失败/拥塞不回退Tunnel，关联释放原flow容量。
- 冷V3扩展`TcpSynthetic4`与`TcpOwned`，Rust/Go`repr(C)`从120→128B、外壳336→344B，同步当前Go装配result blob（不修改历史pin）。**公共Go配置默认TcpOwned=0，确保未获得当前代synthetic/32 route CAS与精准Defender Allow时任何Direct TCP仍fail closed**。不从env猜OS权限。
- 这一提交只创建实际路径和已封闭的OS-owned启用缝，非生产启用；新SOURCE Windows/Linux Rust、Go和cross CI待测。后续必须将/32 route与Defender授权纳入同一四阶段WAL存续/失败回滚，才可打开owner grant并执行真D1–D5/P1–P2、padding。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Wire optional real Windows kernel Direct TCP NAT plus physical bound TCP relay and sole Wintun return into native Rust owner while keeping private V3 tcp-owned flag disabled until exact OS route and Defender receipts"}
```
