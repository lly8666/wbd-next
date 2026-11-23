# B45｜Game4/off 原 Go 四条真实 TLS → Rust 单 TUN 四 RAW 与宽错峰

上一批B44产品SOURCE `f193d5829a3d4e8d46078fb1953b2a2b3e98a6ec` [Dual64 #45132376536](https://github.com/lly8666/wbd-next/actions/runs/45132376536) **11 SUCCESS/4 SKIPPED**；三类原App DNS与签名APK已软件PASS，实体Game2业务NOT_RUN。B45不能继承旧源码资格。

本批沿既有 Root App→START Intent→原Go CLI→原 Go 真FakeTCP/SYN/标准TLS/lease+相同epoch→原Rust private group/同一个GameAdapter→原独立M3→同一个TUN接线：

1. 原 Android `runAndroidGame`从只有2条扩为2/4条真实所选Network FakeTCP/TLS lane，各自原Go冷读取/Detach/受保护冷handoff/同代租约，Rust原B39对2/4个lane ID与连续本地端口做 canonicalize；新四条均走原Bionic物理Network。原Linux Game2/4协议/服务器代码不改。所有lane M4 ready后才启用原Root UID私有路由。
2. 原 Rust `AndroidGameWorkers`依group真实2/4动态创建一个TUN TX + N个独立RAW RX M3线程、原 `GameReceiveOwner` 首份IP回TUN、原PN/AEAD/replay不改变。Game4复用原Linux的 `configure_game4_stagger_mode(2)` ：0/4/50/140ms。与普通App数据调用同一个原RAW send的 M4 drain；新增在原TUN eventfd轮询到期时按 `game4_next_due_ns` 继续复制发剩余lane，不因TUN空闲而停止或新开线程。现有原物理/CN/隧道DNS同单TUN owner，Health15/30与九个原Rust计数不变。
3. 原 `rstguard` 仍只建一条精确内核OUTPUT RST rule；Game2旧JSON journal字段保留，新增Game4四连续source-port精确范围和崩溃恢复/Stop Host测试。Normal单端口、Game2双端口行为不改变，不增加Root防御层。
4. 正式Root App新增Game4/off可选项、设置/导出/导入、START Intent/Service校验、原Go真实 `--mode game4`，沿用三DNS/Health/UID路由。原 Rust M4 counts给出Game4独立状态marker，Root App正式解析器兼容Game2/4并强调内核计数非应用E2E。
5. 同批Go RST真实owned test、Java Game4三DNS argv/预设/状态单测和现有B39–B44实际生产源码门，继续只跑自动已配置的Android Dual64双ABI/签名ARM64 APK、Linux原server Oracle与Host测试。GameFEC、Game4热切换、异常工况、额外安全框架仍未接。

B45源码尚待本SOURCE Actions确切结果；Android真实四lane SYN/TLS/认证租约、M4 TCP/UDP、三DNS及UID Stop/性能仍NOT_RUN。代码只在 `experiment/android-temp-root-probe` 和Draft PR#36，绝不视作main合入。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B45原Go四TLS/四source-port RST journal接复用的Rust GameAdapter单TUN四RAW宽错峰+App Game4/off/三DNS/UID/Stop，不改原协议或安全层。"}
```

## B45a｜同批 Go 生产入口组合修复

首轮B45 `1558e784647b3c66f740838477bd761b93d56e65` [Dual64 #45136996614](https://github.com/lly8666/wbd-next/actions/runs/45136996614) 原Rust ARM64/x86编译完成，Android Go编译FAIL：最终计数日志编辑不慎覆盖 `game_android.go` 四lane代码为旧Game2导出，但CLI/bridge已指向 `runAndroidGame` 和 `V4AndroidGameProduct`，造成四个undefined。本修复从已准备好的真实四lane Go Blob恢复，保留B45的四TLS/四端口/Group M4/Stop，同时对齐Linux `int(c.gameLanes)` 策略参数类型，并在实际原Go低频读数按Game2/4打印对应M4 marker供Root App解析。首轮失败证据保留；新SOURCE独立验收，绝不继承旧BUILD_PASS。
