# PLAN029 H1930｜原 Go EXE 进程高CPU其实主要落在原 Rust TX/RX 两线程

- 历史源锁 H1922 Original Win2025 signed Wintun/Npcap/WSL2 Action43716329886 与 H1927 Action43721447384 均 SUCCESS，原有源和artifact未变。本次只离线提取 Windows 原 Go 宿主进程的 Rust 线程 ID，**未改变任何网络产品热路径，不触发Windows原生Actions**。
- Go 源码 `r0/go_overlay/internal/realityfront/bridge_v4_windows_native_io.go` 明确声明同进程原TLS Rust ABI仅冷启动，业务packet不再跨Go/Rust；`r0/go_overlay/cmd/wbd-client/m0_native_v4_rust_peer_windows.go` 则明确两条 Rust native worker处理稳态 Wintun+Npcap读写/AEAD/Send。Rust `v4_windows_native_runtime.rs` 已在 TX/RX启动时精确打出 Windows OS TID（H1922 TX7868, RX4180），不必添加新产品ABI。
- 现有 `tools/m0_wl_native_resource_sampler.py` 每秒 Win32 GetThreadTimes 并保留前6热线程 ID。由于所有历史 `GetThreadDescription` 返回 `HRESULT_10000000`，`named_rust_workers=0`，过去把Rust误标为“其他线程”或从Go EXE进程CPU推测Go热路径不成立。H1930以原 Rust日志 TID 对照Win32线程采样的**精确整型ID**；采样缺项不归为Go，源SHA/两worker ID/Windows进程唯一PID/Action结论逐项严格核验。
- H1922原进程191个1Hz样本累计CPU约61.75s，Rust TX42.328125 CPU-s（24.5625user+17.765625kernel）、Rust RX16.765625 CPU-s（2.515625user+14.25kernel），**TX+RX合计≥59.09375s，至少95.7%**。按同机约34秒500Mbps阶段，物理 TX/RX 0.3594/0.1406s vs Direct 18.5156/6.4375s（Direct阶段占线程采样99.07%）；按约37秒双向700Mbps，物理 TX/RX 0.4531/0.1094s vs Direct 22.25/9.75s（98.51%）。均为1Hz与前6热点线程保守下界、阶段边界约1秒误差。**高CPU应先优化Rust TX event/WSA/read-write/ready工作，RX次之；不先改Go冷热边界。**
- H1927短4MiB+384小TCP：总1.4375 CPU秒里明确Rust TX0.390625s、RX0.09375s，约33.7%；**它不是持续500/700Mbps负载**，不能反驳H1922高负载99% Rust，也不能把其他线程算成Go。
- 新 `tools/m0_plan029_rust_thread_cpu_attribution.py` 对签名Action原ZIP只读审计，要求预先由GitHub确认 `--action-conclusion success` 才输出仅限CPU归属PASS；Action红保留review，SOURCE不匹配、缺ID/半损采样立即失败。8项毫秒级纯单测加到治理CI，避免今后含糊归因；不需要原生Windows编译。
- 4MiB H1927产品正确性、384小TCP p50新增0.45–0.66ms但首回包p99达15ms、10GiB H1922 吞吐/FIN/Stop保持既有原签名PASS；H1926 stack续票CPU实际降幅**仍NOT_MEASURED**，下一个更改需相同Windows VM新旧二进制或源锁阶段对照且严保any-progress self-ticket，不能再用H1915激进抑票造成真挂死。

```feature-impact
{"kind":"none","ids":[],"reason":"Read-only offline original Rust Win32 TID CPU attribution and governance unit tests; neither runtime product nor feature status changed."}
```
