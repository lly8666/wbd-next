# Android CN geosite 第一轮编译失败（2026-11-17）

- SOURCE `341024376aff03385a492d68506cbb1fa74769b3`，[NDK Action43943399099](https://github.com/lly8666/wbd-next/actions/runs/43943399099) **FAIL**、[KSU Action43943399080](https://github.com/lly8666/wbd-next/actions/runs/43943399080) **FAIL**，两者都是 Rust E0277：`Policy` 派生 Debug 但其新字段 `cn_geosite::Index` 没有实现 Debug，未运行 APK打包/虚拟机；regex 1.12.2 / sha2 0.10.9 下载与编译正常。
- 修复仅在 `Index` 声明前增加 `#[derive(Debug)]`，保持原政策、数据和安全范围不变；后续源码重新 KSU CI 时新的数据源 ZIP/Root UI校验需真实成功才能算 PASS。此历史编译 FAIL 不被改写。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix Rust E0277 Debug derive in new Android geosite Index; first source-locked dual-ABI compile FAIL preserved."}
```
