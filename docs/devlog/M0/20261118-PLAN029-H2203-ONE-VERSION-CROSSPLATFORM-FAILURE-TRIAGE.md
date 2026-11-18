# H2203｜单版本加密控制跨平台红灯排查

当前H2202产品SOURCE `2ca956b9bffdb4d8712de2a8e5d2f18e12fcc244`。原生两ISA Linux真网络 [44311389695](https://github.com/lly8666/wbd-next/actions/runs/44311389695) SUCCESS；Win2025/Linux x64/ARM Go TLS [44311389786](https://github.com/lly8666/wbd-next/actions/runs/44311389786) SUCCESS；Android APK + NDK + OpenWrt musl [44311389808](https://github.com/lly8666/wbd-next/actions/runs/44311389808) 构建SUCCESS，非设备实测。

原红灯保留：[44311390284](https://github.com/lly8666/wbd-next/actions/runs/44311390284)治理、[44311389999](https://github.com/lly8666/wbd-next/actions/runs/44311389999)维护，M0 combined hot 32791 > 32768；本次仅压缩热cursor，不改预算。[44311389952](https://github.com/lly8666/wbd-next/actions/runs/44311389952) Windows exact-blob 装配3处清单旧SHA（linux.go、game_linux.go、admission_v4_test.go），本次以真实当前Git blob更新，未放松检查。[44311389970](https://github.com/lly8666/wbd-next/actions/runs/44311389970)原Go pinned TLS 21 PASS、1 FAIL：退役旧V3客户端不能解析新V2随机拒绝回包，客户端超时，服务端正确ErrAdmissionVersion。本次负测保留服务端严格版本拒绝和客户端必须失败，不再要求已退役客户端准确返回新版错误码。不恢复任何旧协议兼容。

本批仅修测试断言、清单与治理，无基础业务包/认证热路径改变。Windows原生Wintun/Npcap与Android/OpenWrt实体、公网DPI、跨ISA/p99/CPU NOT_RUN；029完整技术OPEN，030未启动。