# B81｜共享官方 CN 域名快照及 App 冷导入/恢复

基线 B80 `b2ab6d675565f7f9f00b2366c7b19fa285f8e61d`，Draft PR #36，仅实验分支。历史 A48 真机 Normal/off TLS/认证/租约/M4 RAW/TUN 双向及 Stop 已观察，独立 TCP/UDP 逐字节与新 SOURCE 设备/性能仍 NOT_RUN。

- 复用 main `cn_domain_snapshot.py` 的官方 flattened release 下载/选择，Android adapter 将四种原规则转成现有 typed text；旧 CN8503 验证不改写。APK 默认打包新数据；App 可手工导入 main 兼容文本并恢复内置，下一次 START 使用；不做后台下载或 FakeIP。
- 原 Go 冷 canonicalize 一次，原 Rust M4 matcher 处理 suffix/full/keyword/regex，Normal/Fixed/Auto/Game 共用原 FFI；去掉生产固定8503数量耦合，实际 native readback 与本次字节计数一致。CN split OFF 跳过 Go matcher 加载。无 Java/Go 普通 DATA 热路径、新线程或额外防御框架。
- B80 [产品 #45356590332](https://github.com/lly8666/wbd-next/actions/runs/45356590332) 8 SUCCESS/2 FAIL/5 SKIPPED：原 ACK/SACK 独立 rustc 不再能编译，改原 crate Cargo 测试；旧 Game RX 源断言适配 B80 ACK/DATA；APK 旧 NativePayload 构造断言同步实际参数。维护 831 项仅 assemble.py 旧 pin 失败，实际合入 main blob 为 39ee7800d89cfd4a2c634d5e0280f9f5f951f2ec；历史 pin 不改。本批实际 CI 待判，不额外派发 KSU/TAP 或实体测试。
- 下一步收本 SOURCE 正常软件资格；继续 main 已合入的产品大类适配，不扩极端工况。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Shared official CN domain release assets, explicit local import and reset, four typed native DNS rules with dynamic count; B80 existing test entry compatibility fixes."}
```
