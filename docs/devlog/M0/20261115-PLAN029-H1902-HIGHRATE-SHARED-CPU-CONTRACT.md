# PLAN029 H1902｜复用CPU计数函数：新测试只查实际共享来源

- H1901 [Action43688821106](https://github.com/lly8666/wbd-next/actions/runs/43688821106) 的四项高率Python单测前三项PASS：确切500Mb/s与700Mb/s/512+256+256MiB/64KiB流式预算、同一真实socketpair双向thread同步与SHA、GetSystemTimes host含idle量纲。最后一项断言误认为CPU作用域`WIN32_ORIGINAL_GO_PLUS_RUST_PROCESS_WITH_TUNNEL_UDP_NO_DRIVER_ISR_DPC`常量在H1898本文件，实际按代码复用H1896 `cpu_delta` 的原定义，编译前静态FAIL；旧H1894/H1896测试均已通过，故尚未启动签名原生场景。
- H1902只修断言检查H1898确实调用`cpu_delta`于**原Go+Rust PID**及**独立Python发生器PID**，并在共享`tools/m0_plan029_h1896_sustain_tcp.py`验证原CPU作用域。目标速率/真SHA/FIN/Stop/96B UDP时间戳、Windows整机CPU采样、Windows/WSL2生产代码完全不改，也不通过重复字符串糊弄独立CPU归因。
- H1901 [治理与Feature Action43688821104](https://github.com/lly8666/wbd-next/actions/runs/43688821104) 双项SUCCESS，原32768热预算未放宽。重新运行带显式`[plan029-v3-real-p2-bulk] [plan029-v3-real-p2-500-700]`的真Normal原Windows2025↔WSL2单一SOURCE；500/700只是目标，实际速率、发生器/host CPU、双Stop未出结果一律NOT_RUN。PLAN029仍IN_PROGRESS，P1/P2 OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"H1902 fixes only mistaken high-rate static CPU source assertion by checking actual imported H1896 implementation and real H1898 call sites; no feature or network product edit."}
```
