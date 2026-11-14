# PLAN029 H1859｜P1 B段先失败于源码编译特性门；4MiB场景被scope误跳过

- [H1857 Action43613384092](https://github.com/lly8666/wbd-next/actions/runs/43613384092) SOURCE `867612d2`：P1 A原V4/off真实50Mbps/25ms无损60s，Windows 49.9996Mbps、Linux49.9866Mbps、0.69839实际GiB、Win Go+Rust CPU13.5156s=19.3524s/GiB，Windows RTT p99 63ms、最长空洞46ms，双端owned Stop PASS。B在原Windows Go启动时`wbd_m0_win_native_v3_start`缺导出，**尚未开测**；不能当成P1 CPU回退或网络失败。
- [H1858 Action43614737936](https://github.com/lly8666/wbd-next/actions/runs/43614737936) SOURCE `13312046`：Windows Go/Rust、Linux Rust组件/编译PASS，**native-public-two-os SKIPPED**，不能当4MiB P2 PASS/FAIL。查明`tools/m0_native_ci_scope.py::EXPLICIT_NATIVE_MARKERS`遗漏`[plan029-v3-real-p2-bulk]`，并且workflow V3 build/trial、Direct、外层1460及TUN MTU1460条件仍只认旧1MiB marker。
- H1859针对**同一根因**一起修：P1/A-B单场的builder虽然脚本对child设置0/1但构建时没有`m0_v4_probe`，本SOURCE的`WBD_PLAN029_NATIVE_V3_TRIAL`编译选择包含P1 marker，使DLL一次性有V3导出；P1 A仍显式child trial=0/B=1。4MiB bulk marker在source scope、V3 build/Direct/MTU条件中完全并列，下一独立SOURCE才运行bulk，避免此提交一Action混两场。
- 未改旧28矩阵、TLS/Defender/WAL或性能参数，不调RTO/Nagle/64KiB。此commit仅`[plan029-v3-real-p1-tunnel-ab]`一场重测，真实B结果**NOT_RUN_AT_COMMIT**；失败/NOT_RUN保留。继续所有029出口。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1859 updated this feature card with scoped negative P1 B missing V3 export and H1858 bulk native skip; status still experimental, no product performance promotion."}
```
