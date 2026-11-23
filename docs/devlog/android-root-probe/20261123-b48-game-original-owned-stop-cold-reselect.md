# B48｜原Android Game2/4组Stop→UID/RAW/RST清理→正式App完成收据

## 基线
B47原Go/Rust产品SOURCE `c3067af60b7013327907842c0148c5613a3199a8` [Android Dual64 #45158643764](https://github.com/lly8666/wbd-next/actions/runs/45158643764) **completed/success：11 SUCCESS / 4 SKIPPED**，包含原双ABI、签名Root APK、两原Linux Server Oracle、6原DNS/CN/M3 Host与单纯Android宿主资格。B47 Service修好真实 Game2/4 M4 READY但**原Go Game没有完整组停机/路由收据**，所以App仍不能确认 Stop 之后安全冷选Network；B47开发日志真实NOT_RUN保留。

## B48 同批实际产品施工

1. 在现有原Go `runAndroidGame` 中保留单个真正的Rust GameAdapter、两/四真FakeTCP/TLS lanes、原Bionic单TUN/独立RAW worker、RST durable journal。修改原Go defer**停机先撤销本次私有UID路由并读回**：只有 `undoRoute()` 实际返回nil才打印原Normal共用 `V4_PUBLIC_ANDROID_UID_ROUTE_STOP_DRAINED role=client`；失败必须合并原错误，但仍执行 `native.Close()`。之后Rust `game_group_stop` join所有M4 worker、StopAndReleaseOriginalOwner逐条release、group release并撤销原verified身份。任何Rust错误不宣称完成。
2. 在后执行的外层原Go cold defer中停止/join所有已建FakeTCP RTO（既有幂等行为、错误不再丢弃）、逐条Close真Go RAW IPv4 endpoint解阻塞、`readers.Wait()`、关闭关联，以及一条原持久 `rstguard.Close()` 精确journal/RST移除。保留guard失败底层error。**只有此前实际Game产品READY且最终retErr==nil**才发 `V4_PUBLIC_ANDROID_GAME_STOP_JOINED role=client lanes=N rust_m4=joined uid_route=settled rst_guard=cleared` 与共用 `V4_PUBLIC_NATIVE_STOP_DRAINED role=client`；一切失败不发伪完成，未安装路由也不声称已经实际撤销路由。
3. 原正式 Service 继续识别Game2/4 off/fixed真实 `V4_ORIGINAL_ANDROID_GAME_NATIVE_READY`、实际UID_ROUTE_INSTALLED；现追加必须**同一个Game N 的组Stop**、Native Stop、若实际安装UID route则有撤销收据、原Go进程确切EXIT0，才展示 `OWNED_STOP_VERIFIED`。单独Go root PID信号接受、Rust M4 counter、Game4宽错峰/FEC恢复候选或仅普通Native Stop均不等于Game完整退出。新固定枚举 `ORIGINAL_GO_GAME_GROUP_STOP_JOINED` 写入现有仅枚举的安全本地日志，不录用户名/密钥/packet。
4. 原 `RootClientActivity.start()` 在 Activity→Service异步派发的短间隙也先占用 `startDispatchPending`：仅第一合法START可写私有凭据，Service实际接到START后由 `sessionOwnerActive` 接管，非法/失败请求归还；显式冷切网仍是用户点Stop→等旧owner结束→刷新当前Android Network→人工选新实体Network→重新START/Go TLS，不把Android丢网回调变成Root自动重启。所有路线继续复用原UID/secret/MTU/DNS/Go/Rust数据路径。
5. 加强官方纯JVM `RootGameSessionStatusTest` 覆盖Game2/4 off/fixed正反组Stop、错误lane、RST未清、组M4未join、Native/UID/EXIT失败组合及Normal原行为； `test-network-scope-gate.sh` 静态检查真正Go defer层次、先撤route后Close group、保留每处原错误、Service/Game对应group和异步START owner，并由官方签名ARM64 APK Job执行原生产Java/Go/Rust源码。

## 不混淆的验收边界
B48仅在 `experiment/android-temp-root-probe` / Draft PR #36 源码施工，没有动main/M0，无Android手机与真实用户Linux Server授权或远程部署。每一项B48软件PASS只能由**本SOURCE** Android Dual64原Go/Rust ARM64+x86_64、签名Root APK/JVM Host、两个Linux原Server Oracle/六个Host和功能治理完成后记录。真实Android Game2/4 off/fixed TCP/UDP/DNS业务、Stop/真正切网、CPU/吞吐仍 **NOT_RUN/NOT_PROVEN**。不做无缝热切换、GameFEC Auto、极端网络防御或新的逐包Go/Java循环。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B48原Go Game2/4组级真实Stop接UID先撤、Rust单GameAdapter M4 join、多RAW与持久RST清理后双收据；正式App校验Game专属Stop和异步START冷切网单Owner。"}
```
