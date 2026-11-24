# A17c x86 KSU 原 Go ELF help 的真正退出语义（2026-11-18）

[A17b Action44232432179](https://github.com/lly8666/wbd-next/actions/runs/44232432179) D0 ARM64/x86 Bionic 原生编译、原 ARM64 APK 和 Linux oracle 各自 SUCCESS；Android16 x86 KSU job 源锁 signed CI APK、KSU 真实 shell root、Activity 和实际原 Go ELF 均执行。其正式源码 `wbd-v4-client-amd64 --help` 打印完整 40 项原客户端参数和 `flag: help requested`，命令退出 1；原因是原 Go cli 的 `flag.ErrHelp` 返回到调用 `log.Fatal` 的 main，不是内核崩溃。原上传工件 14394749946 内 go-help-code.txt=1、go-help.txt 实际可核对。旧脚本要求 rc=0 而将此错记 FAIL。

本次只修订测试脚本和脱敏 receipt，必须真实 rc1 且包含固定原 Go Usage、android-network-handle/raw-interface/tun-name/username 以及 `flag: help requested`，拒绝 panic/fatal error；不宽容其他 rc1。不变更原 Go TLS、Rust 原 M4、API 权限、ARM64 signed APK 或 DNS 禁用状态。新源码 Actions 未完成前 D1 部分仍 NOT_PROVEN；App→su/真实 TLS、租约、M4 TCP/UDP/Stop 均 NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"修正 x86 KSU 原 Go ELF help 的真实 flag.ErrHelp/exit1 验收，不更改原产品；严格校验 Usage/关键参数/正确 ErrHelp 并拒绝其他 rc1。"}
```
