# B47｜正式Root App Game2/4真实READY、双Stop收据与显式冷Network重选

**基线**：B46a产品SOURCE `3952345601d3bd77e9f8c6f5bc4c0938a6b9b438` [Android Dual64 #45144428626](https://github.com/lly8666/wbd-next/actions/runs/45144428626) 11 SUCCESS/4 SKIPPED，双ABI、Root签名APK、两个原Linux Server Oracle和6个DNS/CN/M3 Host全PASS；B46a日志已归档，Game实体NOT_RUN。实验分支PR#36仍Draft，main/M0不写。

## 本批实际接线

1. **Service原Game READY漏接修复**：此前 `RootClientService` 只匹配 Normal `V4_ORIGINAL_GO_CLIENT_NATIVE_READY role=client`，忽略原Go `runAndroidGame` 在真实2/4 Go TLS/认证、Rust group M4、后UID路由之后打印的 `V4_ORIGINAL_ANDROID_GAME_NATIVE_READY role=client lanes=N original_go_tls=1 original_rust_m4=1 uid_route_after_m4=1`。B47以正式纯Java `RootGameSessionStatus`严格匹配已选模式Game2/4 off/fixed与真实lane数；与原App `V4_PUBLIC_ANDROID_UID_ROUTE_INSTALLED` **两者同见**才能显示Game M4+UID READY。未将单纯UI模式、FEC source/recovered候选或Linux host oracle当成Android实体业务成功。
2. **Root Stop与可重选状态**：Service独立记录原 `V4_PUBLIC_NATIVE_STOP_DRAINED role=client`、`V4_PUBLIC_ANDROID_UID_ROUTE_STOP_DRAINED role=client`，且确有本次原生READY、程序退出code0之后，才显示 `OWNED_STOP_VERIFIED`；缺任一收据均不声称新物理Network热切换成功。原Root的journal恢复仍由现有 `RESTORE` 按钮和Root CLI处理。
3. **普通用户显式切网流程**：Activity提供“切换实体Network：STOP旧会话，再刷新并手动START”；正运行时仅请求原精确STOP，不保存/替换旧原生凭据，不生成新根权限。旧Go/Rust退出后使用Android真实ConnectivityManager重新枚举并由用户自己选WiFi/蜂窝/有线，随后走旧 `start()` 所有完整私有凭据写入、UID身份快照、真SYN/标准TLS/租约、原Rust M4和owned路由。App生命周期新增 `sessionOwnerActive`，活跃期间不再允许二次START覆盖旧凭据。
4. **Host与签名App门**：新 `RootGameSessionStatusTest` 用所选Game2/4固定/off、错误lane、非真实Go时间前缀、伪造READY和缺失Stop收据的正反例执行生产解析器；`test-network-scope-gate.sh` 加新源码门及纯JVM执行，用原source锁ARM64 APK编译实际Service/Activity。固定模式、三DNS、UID选包、Stop/Restore现有回归保留。

## 严格未完成边界

这一轮不会自动在Network lost事件上进行Root重启，不做热替换/Game lane rotation、不使用Android VPN或Java逐包。**Game本身目前尚未向Java输出与Normal一致的两条完整Stop日志；即使旧Group内部真实Close成功，B47也不会为Game宣称 `OWNED_STOP_VERIFIED`**。这需要以后在原Go组级真实结束之后单独接收据；它不是一次JS/JVM模拟就能解决的。当前实体Android Game2/4、Stop/冷切网、应用TCP/UDP/E2E/性能仍NOT_RUN。本SOURCE只有软件/Host/签名APK经真实CI全PASS后可记软件资格，不能继承B46a。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B47正式Android App接真正Game2/4 Go/Rust READY、Host解析/Stop收据判定与显式旧Root先Stop再手动冷选网；不替代原Go/Rust业务或发明自动切网。"}
```
