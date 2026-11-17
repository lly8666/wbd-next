# PLAN029 H1961｜H1960 两个非业务前置失败：恢复 pin blob、热文件预算

- 原 `main` H1960 SOURCE `c34a6881dbe5de03715d1a0b3450a2ae5f830e5c`。真实 Windows/WSL2 DNS/GUI/Stop **NOT_RUN**，因为 [原普通 Win/Linux Action43795958866](https://github.com/lly8666/wbd-next/actions/runs/43795958866) 的 `prepare_windows_wiring.py --check-only` 先拒绝 `m0_plan029_cold_split_windows.go` 的 pinned Git blob mismatch；[Windows 编译43795958940](https://github.com/lly8666/wbd-next/actions/runs/43795958940) 和 [GUI 构建43795958858](https://github.com/lly8666/wbd-next/actions/runs/43795958858) 同样拒绝装配，不是 Go 功能测试或系统 DNS 网络失败。
- H1960 对 `r0/go_overlay/cmd/wbd-client/m0_plan029_cold_split_windows.go` 与 `m0_plan029_cold_split_windows_test.go` 两个文件做了冷单DNS零地址/广播地址拒绝与3模式×2无效值×2方向单测，却漏改 `r0/go_overlay/assembly/manifest-plan020-m0.json` 里**仅这两个 `result_blob` GitSHA**。本轮只把SHA替换为实际 H1960 两文件 blob `b05ec84ae...` 与 `aa57526e...`，其他137个 operations、legacy pin、目标路径与源码不动；不能放宽或删掉 source-lock。
- [原治理 Action43795958874](https://github.com/lly8666/wbd-next/actions/runs/43795958874) `Feature` 的121个 Python unit **OK**，但 `governance.py validate` 的 combined hot-read 超出32768B上限 **169B**（32937B），因此两个治理 job 均 FAIL。仅把 M0 cursor 当期叙述压缩、仍保留8条上下文、两条同 SOURCE H1958 真 D1/D2/P2 证据及 `last_tested_source=ab224ae...`，大段原文在本 devlog 与旧文件保留。
- **未变**：普通产品 early physical preconnect OFF、无备用DNS、无新增第三出口/路由/WFP/Go热泵、无新 P2 场景 marker。H1958 真原生业务止于限定PASS，D1–D5/P1–P2/GUI/Game4/IPv6并不因此合格。H1961 CI 原装配、Windows CLI/GUI build、纯Go单DNS验证与治理需独立收。

```feature-impact
{"kind":"none","ids":[],"reason":"Only repair two exact assembly manifest blob SHA pins and reduce M0 cursor hot-read budget after H1960 source-lock preflight; no new product behavior, feature card remains unchanged."}
```
