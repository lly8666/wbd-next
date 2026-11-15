# PLAN029 H1905｜长负载上限静态断言与真实表达式一致

- H1904 [Action43691627759](https://github.com/lly8666/wbd-next/actions/runs/43691627759) Cheap CI：旧H1896静态测试、CPU/GiB测试及H1903实际socketpair双向SHA、符号CPU delta测试全PASS。只剩新H1903一条字面断言FAIL：测试找 if LONG_RATE:MAX_SUSTAIN=60000 ，源码真实为 if HIGH_RATE:MAX_SUSTAIN=60000 if LONG_RATE else 14000 。同时满足短14000和长60000的分支语义，没有运行原Windows/WSL2原生Job，不能宣称网络已测。
- H1905唯一源码改动：新静态测试精确验证当前完整条件，旧14k与长60k共同检查；不改长测试流量、Windows/WSL2 OS应用、Rust/Go data plane、96B UDP、SHA/FIN/owned Stop。新SOURCE用三显式CI marker重新执行同源 signed Normal 2GiB 500Mb/s 单向和两向各1.5GiB 700Mb/s聚合，物理先Direct后；所有性能结果仍NOT_RUN。
- H1902已签名短测试499.965/699.760Mb/s及Go+Rust13.6875/12.125 CPU秒/GiB，但时长8.59/6.14s，不能据此报告30s持续负载。PLAN029/P1/P2 OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"H1905 fixes only H1903 new source-locked Python test literal to verify exact short 14000 / long 60000 conditional; no feature or product code change."}
```
