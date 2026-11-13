# PLAN029 H1764｜修原生工作流Rust源码漏触发，不重复独立dispatch

- H1763 `c40d1c41`已修真实Direct TCP双腿结束后反向NAT过早删除，提交带 `[plan029-v3-real-direct-udp]`，但原M0 Windows↔WSL2工作流 `on.push.paths`只列Go/夹具/少量Rust Game文件，**没有列入 Direct TCP actor、NAT、native ingress/runtime/platform socket**；因此有组件编译Action，却没有签名产品E2E，不能声称已测。
- H1764在**现存同一个** `m0-wl-public-normal-full.yml` 增5个Rust所选Direct源码触发路径；仍需消息显式029 marker才能执行单Normal实网，其他场景不会被重新激活。现有便宜检查包含对应测试，锁下一SOURCE。无主动workflow_dispatch、无新Agent/Watchdog、无跨改动覆盖。
- H1763 Linux Rust/WinGNU cross已编译PASS，Windows2025组件结果当时仍在途，不代替本次完整Windows真实32KiB+FIN交付。收H1764签名场景时保留H1762首错与STOP清理，D1–D5/P1–P2/Padding/GUI仍OPEN。
```feature-impact
{"kind":"none","ids":[],"reason":"H1764 only repairs CI trigger and scope test; H1763 product change card already recorded with exact prior real FAIL"}
```
