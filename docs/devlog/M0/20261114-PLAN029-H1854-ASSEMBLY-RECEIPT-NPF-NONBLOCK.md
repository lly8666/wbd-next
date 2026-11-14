# PLAN029 H1854｜H1852 首阻断：Go overlay装配blob未随源更新

- H1852 `df26d8c6` native Action [43610536189](https://github.com/lly8666/wbd-next/actions/runs/43610536189) 首个失败在 Linux cheap `prepare_windows_wiring.py --check-only`，报`assembly blob mismatch: r0/go_overlay/internal/faketcp/npcap_native_handoff_windows.go`，故Windows编译、签名Npcap/Wintun、真实P2均**NOT_RUN**；不能说非阻塞策略实网失败。
- 两个changed Go overlay源和纯测试从冻结Git树读取精确blob SHA，同步至`r0/go_overlay/assembly/manifest.json`两个对应operation，不改变donor完整性、其他装配项或执行门槛。不修改H1852 Npcap代码：原Go reader join后一次set/get nonblock、失败精确owned回收，Rust仍事件空闲等。
- H1853卡片容量恢复提交不派网络；H1854新冻结SOURCE仅一次`[plan029-v3-real-p2-rebuild]`签名Normal P2，先过manifest、Go Windows编译和source hash，再实际测1MiB Direct+持续Tunnel UDP；所有实测在提交时NOT_RUN。029仍IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Update only precise assembly manifest blobs for two already committed changed Npcap Go overlay files, preserving pinned donor and original native product execution rather than bypassing integrity check."}
```
