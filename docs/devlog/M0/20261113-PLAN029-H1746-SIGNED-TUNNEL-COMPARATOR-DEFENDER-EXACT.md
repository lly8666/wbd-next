# PLAN029 H1746｜新签名双出口场景的 Windows TCP 测试规则精确源地址

- H1745 SOURCE `947c116aec665c196d657ef1aa5974b54c5522e3` [签名Action43422444895](https://github.com/lly8666/wbd-next/actions/runs/43422444895) 同源cheap/Win+Linux Rust及Windows Go、Linux Rust peer编译通过，真正签名Windows/WSL2 native job当时**IN_PROGRESS**；不把正在执行写成实际Direct PASS或FAIL。
- H1745 **测试专用**新增非CN Linux TUN别名`203.0.113.77/32`，让原Windows→Linux UDP/TCP真正按CN规则走Tunnel；对向Linux→Windows TCP其真实源正是`203.0.113.77`。但原真实Windows Runner临时Allow的RemoteAddress固定为`10.66.0.1`，会拦这一条真实TCP测试，造成不可信的基线FAIL。
- 只修现有测试规则：若且仅若`WBD_PLAN029_V3_DIRECT_SCENE=1`，把**一个**Rule 的`RemoteAddress`改为`203.0.113.77`，其他场景仍`10.66.0.1`；本地只`10.66.0.2`、TCP45902、严格源地址、同Action独占名称、New后Get-NetFirewall*读回、finally删除不变。不是产品Direct kernel TCP的Defender规则；没有全局关闭/开任意端口/放宽系统policy。
- 本源需再次真实Windows签名小场景取独立完整证据。保留H1745当时仍在途SOURCE与今后首FAIL，不能将H1743 Tunnel-only结果外推成双出口。D1–D5/P1–P2和padding未收口。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Scope existing owned Windows real-test TCP firewall rule to exactly the H1746 non-CN Linux TUN peer address; keep prior signed H1745 SOURCE immutable and product Direct TCP disabled"}
```
