# PLAN029 H1895｜H1894 原生CI首错：P2 Windows高精度RTT必须只用perf_counter

- [H1894 Action43681882700](https://github.com/lly8666/wbd-next/actions/runs/43681882700) 旧静态契约`test_h1861_p2_p99_uses_high_resolution_same_windows_clock`检查原P2所有真实Windows RTT时钟只使用`time.perf_counter()`，不允许字符串`time.monotonic()`混入同脚本；H1894新增前后8s CPU/UDP phase recorder使用了4次后者，导致cheap workflow FAILURE，Windows Go/Rust/WSL2签名真实业务尚**NOT_RUN**。新`test_h1894_same_original_process...`已PASS，不得把该静态失败当作网络回归。
- H1895仅把原`tools/m0_plan029_h1815_p2_real_mixed.py`内新加的**四处**`time.monotonic()`统一为原有`time.perf_counter()`，保持真实Windows UDP RTT开始/结束和两个phase窗口均采用Windows原进程系统内同一个高分辨率QPC时间基；原CPU sampler的Win32 1Hz时间戳由同一Windows系统单调时钟收集。用旧H1861及新H1894两种断言同时保证不会再次混用，不放松99th或原H1892真128 SHA/FIN。
- 不改任何生产Rust/WinSock、CPU采样频率、Tunnel包形状/序号或本场128条真Wintun TCP连接；源锁定签名重跑仍需真实前8秒pre128和后8秒126 idle、同Windows Go+Rust进程采样及两段96B UDP p99，并有原Rust128 NAT日志和owned Stop。所有新SOURCE网络**NOT_RUN**。H1894历史FAIL保留，PLAN029仍IN_PROGRESS，P1/P2性能不因减少空读或场景绿灯冒进关闭。

```feature-impact
{"kind":"none","ids":[],"reason":"H1895 only fixes four P2 test fixture clock calls to preserve the established one high-resolution perf_counter RTT clock and corrects test assertion, no product feature change."}
```
