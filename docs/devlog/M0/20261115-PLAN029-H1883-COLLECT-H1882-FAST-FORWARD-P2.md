# PLAN029 H1883｜H1882 新直送SOURCE原生实测结算（无跨VM性能因果假设）

- [签名原生Action43667025249](https://github.com/lly8666/wbd-next/actions/runs/43667025249) exact SOURCE `37c6025629f76d082b080dfb786a46f436ace58b`，Windows2025原Go+签名Npcap/Wintun+Rust CN selective FakeIP/TCP 与WSL2 Linux真实两内核腿：无人工pause 4MiB真交付和同SHA/半关闭PASS，物理47.233ms（上传18.159/回传14.691）→FakeIP Direct115.862ms（上传51.444/回传47.052），额外68.629ms/2.453倍，同一runner物理vsDirect。
- Tunnel小UDP覆盖整个Direct生命周期，Windows/Linux各120/120唯一交付、Win小包p99 2.324ms、最大gap17.889ms；双owned Stop及OS恢复PASS。原Windows与Linux Rust组件/Go编译PASS。当前 `direct_forwarded`与`queued_copy`聚合值未从driver逐字节artifact重新证明，不要把代码推断当实测CPU节省。
- H1877历史物理50.606/Direct141.030ms（2.787倍）来自**另一runner**，H1882的2.453不是可信旧/新算法A/B。P2性能仍OPEN，P1纯Tunnel +9.41% CPU/GiB另属后端差异，驱动CPU及最老队列年龄NOT_MEASURED。
- 下一项按用户强调的高视角进行**同一SOURCE同VM同一签名Wintun会话的A-B-B-A真实TCP试验**，A旧队列、B无积压直送，由仅`m0_v4_probe`且双重显式CI Scene授权的原Rust actor为同一测试专用端口选择路径，不引入产品用户可用的热路由开关。4条真Direct流均验SHA/FIN/原Linux source及Tunnel UDP持续覆盖全程，Stop独立要求PASS。算法因果只在此试验的A/B签名结果后再判断，继续D1–D5/GUI/Game4/IPv6缺口。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1883 collect source-locked H1882 genuine physical-vs-Direct 4MiB+Tunnel120/120+Stop receipt and keep P2 performance OPEN; next probe-only same-binary A-B-B-A."}
```
