# PLAN027A H927｜原始 Windows Go 夹具跟随 Rust ABI

恢复 H926 `91f244147c07be7a201c00258a4aca85313070a8` 自动 Action `41434561392`：source-locked PLAN020 assembly **通过**，在 Go CLI `m0_native_v4_reauth_windows_test.go:67` **失败** `undefined: m0WindowsV4PeerRecordCap`。这是 H924 刻意移除重复 Go 公式/1400 帽后漏修的真实旧测试，不是 Wintun OS Applied 失败，也不能擅自写成 PASS。

本批将测试改成纯 Rust ABI C 布局36/40/32及模式 0/1/2/3 映射，原数学向量只在 Rust `v4_mtu_budget_ffi.rs`，不恢复第二套减法。新旧 source 的 FAIL/PASS 分别保留。同步更新 `manifest-plan020-m0.json` 中两项 actual Git blob，仍在同一个原 Go/WAL 组装通路，不新增生命周期。

任何 native Windows/Linux MTU 应用、有效 DF0/DF1、Windows Game group、弱网/性能都未由此测试证明。历史 PLAN027 测量不重派。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Recover PLAN027A Windows Go test that referenced the removed hardcoded MTU helper, test C ABI struct sizes/mode only, source-pin both touched originals in plan020 manifest; keep actual MTU and OS qualification pending."}
```
