# PLAN029 H1967｜修正纯前置错误，不冒充真实Windows延迟
- H1966 SOURCE `ad44e387cba9ab9573605b05c4afabc95f381eaa` [廉价 Action43803692519](https://github.com/lly8666/wbd-next/actions/runs/43803692519) 和 [治理 Action43803692572](https://github.com/lly8666/wbd-next/actions/runs/43803692572) 在 `tools/check_workflows.py` 解析 `m0_plan029_h1966_steady_tcp_qpc.py` 时出现**确切SyntaxError 第167行跨行if未加括号**，所以源锁原生P2**未执行**，并不是Windows/Rust/内核性能FAIL。
- 原 [Rust Windows/Linux纯组件 Action43803692711](https://github.com/lly8666/wbd-next/actions/runs/43803692711) 和 [Windows独立 Go/Rust编译43803692573](https://github.com/lly8666/wbd-next/actions/runs/43803692573) 失败在同一 `windows_direct_tcp.rs`：源中已有属于`RelayTick`的derive行被放在新`RelaySteadyQpc`之前，形成重复`Clone/Copy/Debug/Eq`实现；同时原`RelayTick`失去这些traits。H1967只把derive归还`RelayTick`，保留新QPC结构唯一derive，未改socket转发逻辑。
- 同时严格保留Linux guest真实SHA/WinSock bytes/停机QPC关联、source-locked 8192行上限、普通产品所有计时OFF、Wintun RX SendPacket未测的边界。不加预连接，不重测极端CN/非CN同IP。下一签名Action必须在真实Windows/Linux Rust源码编译和7项合成回归绿后才发。
- 旧H1958真Windows/WSL2证据独立有效；H1966静态失败不能记作任何新p50/p95/p99数值。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Repair only source-locked steady-QPC Python multiline signature syntax and move the inherited RelayTick derive back onto its proper type; all original Windows app/kernel source performance remains NOT_RUN pending CI."}
```
