# PLAN029 H1741｜真实Direct flow绑定FakeIP持久地址引用

- H1740 SOURCE `2d3c6cfd84354037e2502e33a1502ab8a43190cb` [Go Windows43410186006](https://github.com/lly8666/wbd-next/actions/runs/43410186006) 和 [governance43410185900](https://github.com/lly8666/wbd-next/actions/runs/43410185900) PASS_SCOPED；旧H1739编译FAIL保留。
- 发现实际原Rust NativeOwner 以前没有调用`FakeAllocator::pin_first_flow`，DNS宣布的FakeIP在Direct物理TCP/UDP活跃期间仍可能超TTL+10min被回收。修正：同一TX owner对第一次fake-backed 5tuple只pin一次，真实TCP relay结束/UDP socket异常或idle退场按精确5tuple release，重复退场幂等。无新Wintun reader、无Go逐包、无文件热路径，UDP retirement每轮最多64个，无Vec分配。
- FakeIP 回收只在既有1Hz粗粒度tick用 UNIX epoch ms，不能错用Rust m2 monotonic。单测覆盖持流跨TTL+10min不重用，退场后允许回收；这不是签名Windows真实双出口验收。
- 新SOURCE CI待跑；Defender、Go V3 Apply→TCP激活、真实D1-D5/P1-P2、padding仍NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Connect original Rust NativeOwner FakeIP first Direct flow reference to actual UDP/TCP socket retirement; use wall-clock coarse safe quarantine"}
```
