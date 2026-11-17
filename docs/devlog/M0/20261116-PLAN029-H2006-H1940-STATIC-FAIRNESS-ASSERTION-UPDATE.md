# PLAN029 H2006｜H1940旧19句柄静态字符串断言更新，Stop/TCP公平性仍硬约束

- H2004 [治理Action43871366628](https://github.com/lly8666/wbd-next/actions/runs/43871366628) Feature Catalog **FAIL**：源码静态单测 `tests/test_m0_plan029_h1940_tcp_event_fair_wait.py` 仍锁原 `let (mut order,n)=native_tx_wait_order(wait_phase,count==19);`、`if n==19` 等19句柄字符串，和 H2002 只增加最多16个UDP event句柄的同一Owner源码不同，并非该次测量业务网络失败。
- H2006 **只修改静态测试**：保留 `native_tx_wait_order` 、旧TCP16 shard原顺序轮转、Stop索引0、WaitForMultipleObjects同一调用，新增断言总栈句柄3+16+16=35、UDP实际最多16、TCP/UDP唤醒分支精确分离。不动Go/Rust代码、Timeout、路由、WFP、FakeIP、产品设置或原签名网络场景。
- H2005修正 WinSock原子ACK必须在recv前并增加Windows内核两连续UDP包重唤醒测试；其源码独立 [原始Windows/WSL2 Action43871804786](https://github.com/lly8666/wbd-next/actions/runs/43871804786) 结果待收。H2002原始Native同源 Action43870817399 按原结果保留，不跨版本混证据。
```feature-impact
{"kind":"none","ids":[],"reason":"H2006 repairs stale pure test-only H1940 source-string assertion for bounded UDP additions while preserving exact Stop/TCP fairness; no product functionality change."}
```
