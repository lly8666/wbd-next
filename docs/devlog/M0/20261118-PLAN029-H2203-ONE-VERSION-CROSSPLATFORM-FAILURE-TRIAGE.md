# H2203｜单版本加密控制跨平台红灯排查

当前H2202产品SOURCE `2ca956b9bffdb4d8712de2a8e5d2f18e12fcc244`。原生两ISA Linux真网络 [44311389695](https://github.com/lly8666/wbd-next/actions/runs/44311389695) SUCCESS；Win2025/Linux x64/ARM Go TLS [44311389786](https://github.com/lly8666/wbd-next/actions/runs/44311389786) SUCCESS；Android APK + NDK + OpenWrt musl [44311389808](https://github.com/lly8666/wbd-next/actions/runs/44311389808) 构建SUCCESS，非设备实测。

原红灯保留：[44311390284](https://github.com/lly8666/wbd-next/actions/runs/44311390284)治理、[44311389999](https://github.com/lly8666/wbd-next/actions/runs/44311389999)维护，M0 combined hot 32791 > 32768；本次仅压缩热cursor，不改预算。[44311389952](https://github.com/lly8666/wbd-next/actions/runs/44311389952) Windows exact-blob 装配3处清单旧SHA（linux.go、game_linux.go、admission_v4_test.go），本次以真实当前Git blob更新，未放松检查。[44311389970](https://github.com/lly8666/wbd-next/actions/runs/44311389970)原Go pinned TLS 21 PASS、1 FAIL：退役旧V3客户端不能解析新V2随机拒绝回包，客户端超时，服务端正确ErrAdmissionVersion。本次负测保留服务端严格版本拒绝和客户端必须失败，不再要求已退役客户端准确返回新版错误码。不恢复任何旧协议兼容。

本批仅修测试断言、清单与治理，无基础业务包/认证热路径改变。Windows原生Wintun/Npcap与Android/OpenWrt实体、公网DPI、跨ISA/p99/CPU NOT_RUN；029完整技术OPEN，030未启动。
## H2204回收/修复Feature声明

H2202原产品SOURCE `2ca956b9bffdb4d8712de2a8e5d2f18e12fcc244` native Linux x86/ARM [44311389695](https://github.com/lly8666/wbd-next/actions/runs/44311389695) 各12=24/24真OS双端PASS_SCOPED，各234 ZIP CRC成功；Win2025/Linux x86/ARM原GoTLS [44311389786](https://github.com/lly8666/wbd-next/actions/runs/44311389786) 3/3；Android APK/NDK/OpenWrt [44311389808](https://github.com/lly8666/wbd-next/actions/runs/44311389808)仅构建3/3。H2203源码 `3f28e330edc4561837ade02d81c625917bd32977` 原Go V4 TLS [44316261405](https://github.com/lly8666/wbd-next/actions/runs/44316261405)、cold [44316261208](https://github.com/lly8666/wbd-next/actions/runs/44316261208)、WinGo/Rust/LinuxRust [44316261253](https://github.com/lly8666/wbd-next/actions/runs/44316261253)、Win CLI编译 [44316261198](https://github.com/lly8666/wbd-next/actions/runs/44316261198)均SUCCESS。原治理 [44316261365](https://github.com/lly8666/wbd-next/actions/runs/44316261365) Governance SUCCESS、Feature FAIL：仅忘填写feature-impact；首次红灯保留。H2202初版热预算/装配SHA/V3旧客户端错误格式等FAIL不涂改。详细[证据](../evidence/M0/PLAN029-H2202-ONE-V2-LINUX-WINDOWS-ANDROID-OPENWRT-SCOPED-20261118.json)及[单版本规范](../decisions/M0-PLAN029-H2204-UNIFIED-TLS-ADMISSION-V2-20261118.md)。物理设备、真Windows驱动/GUI、DPI/p99均NOT_RUN。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"H2203 source-pinned Windows manifest and retired V3 negative-test repair; H2204 exact Linux original 24 native scenes, Windows/Linux Go TLS, Android/OpenWrt build-only evidence, no legacy v1 compatibility."}
```
