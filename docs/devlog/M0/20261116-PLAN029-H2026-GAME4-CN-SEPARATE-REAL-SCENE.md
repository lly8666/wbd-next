# PLAN029 H2026｜单独重触发 Game4 CN四lane原生真实场景
- H2025新填充20..30条、2..3秒、0..500B真MTU无累计budget的Normal原生物理抓包通过另一exclusive tag单场调度，**本提交仅触发Game4 CN**。
- H2023 [Action43894787329](https://github.com/lly8666/wbd-next/actions/runs/43894787329) Game4 Rust DLL V4 ABI、Go/Rust Linux/Windows构建成功，但真正Windows/WSL2启动前场景配置`NameError p029_p2`，所以原真实业务NOT_RUN。H2020源中已后移校验位置，H2024静态网关PASS；本次同Go/Rust产品源码不变、仅新SOURCE单独原场景验证。
- Gate: 4条原Go TLS+Rust GameAdapter、同一Wintun；真实Linux eth0独立Direct DNS53→FakeIP→UDP、32KiB真实Direct TCP+FIN/half-close；独立Game4 Tunnel TCP/UDP、真实OS Apply、Defender、双Stop。任何真实失败按首边界处理，不伪造证据。
```feature-impact
{"kind":"none","ids":[],"reason":"H2026 checkpoint only, dispatch separate original signed Game4 CN scenario while new padding runs independently."}
```
