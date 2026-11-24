# B61｜原 Android Root Service 定时冷轮换与通知栏 STOP

B60a SOURCE `e0e2b7f65b8d9225a3d086927842964f60c8da6f` [Dual64 #45303190692](https://github.com/lly8666/wbd-next/actions/runs/45303190692) 9 SUCCESS / 1 FAIL / 5 SKIPPED。六Host、双ABI原Go/Rust、Linux Normal/off及x86 D2-S0通过；B60新增JVM PASS；root-arm64-app最后旧B24静态onResume顺序断言失败，未进入签名APK构建。本批调整B60的onResume顺序，保留旧断言和原失败记录。

App本次START选0/5/15/30分钟（默认0、暂不跨配置持久化）。仅显式开启时，唯一原Service保留本次非秘密Intent及已有0600凭据文件的准确内容（会话内存，不新增持久明文、不放Intent）。原Go/Rust TLS/Admission、/32、M4、UID真实READY后通过现有Handler注册一次低频deadline；到期触发原owned Stop。旧进程退出、Rust M4和UID实际Stop确认、旧临时文件及Watcher清理后，同一Service精确匹配同一实体Network并重新写入已有私有文件，进入原 `startOriginalOwner`；用户START走同一入口。每代重新原Go FakeTCP/TLS、Rust M3/M4、PN及UID路由。明确短暂断流，非Linux shared-TUN热轮换，不加唤醒锁；普通STOP/恢复/任务移除、物理Network变化、原Stop或后续START失败取消轮换。无新后台进程、周期Network polling、Java/Go逐包处理或新协议，原Go CLI/Rust DATA不变。通知点击返回Activity、STOP action发给原Service。

用户要求先完成功能，实体切换、TCP/UDP/DNS/E2E/CPU统一NOT_RUN；系统netd、IPv6/464XLAT、热点、物理TCP53仍未完成。仅实验分支，main/M0、设备和服务器不动。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B61原Root Service定时冷轮换及通知STOP复用原Go/Rust完整Stop及同一START；修B60旧onResume断言，原协议和数据面不变。"}
```
