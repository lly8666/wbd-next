# A16c：Android 原 Go UID route 同源构建标签补全（2026-11-18）

[A16b Action44230209178](https://github.com/lly8666/wbd-next/actions/runs/44230209178)：真实 ARM64 Rust 以及 x86_64 Rust 原数据面构建均已完成，但 x86 原 Go 编译 FAIL：`linux.go:1469:31: undefined: androidRootRouteAfterNative`，原函数仅在 `android && arm64` build tag 下编入。本次只允许同一份 Android UID route 本体在 `GOARCH=amd64` 一同编译，未改变 route journal、用户 UID 安全限定、权限/密钥，也未复制出 x86 单独代码。新 SOURCE 尚需重跑 ARM64/x86 与原服务端守门。x86 Android 原客户端 Runtime/TLS/M4/Stop 未运行；DNS 接管仍 false，实体 ARM64 未修改。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"修复 x86 Android 原 Go 编译发现的 androidRootRouteAfterNative arm64-only 构建标签，同一原有 UID route 实现供 x86_64 CI 编译；不变更协议、安全或产品 ARM64 发行。"}
```
