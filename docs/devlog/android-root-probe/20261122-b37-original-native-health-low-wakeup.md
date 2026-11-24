# B37｜Android Root 原 Rust M4 Health 15/30 秒低唤醒接线

## 真正缺失的一段

主线原Go/Rust已经存在 `V4LinuxClientProductConfig.HealthKeepaliveSeconds`、`bridge.configureOriginalNativeHealth` 和 Rust `HealthPolicy` 真正effective读回，但Android Root App/CLI无参数，所有真实会话只能15秒Health、90秒认证Peer dead。B37将可选30秒接到现成原Rust HealthClock；默认15秒不改。两端各自已有90秒dead，30秒仍满足Rust 3倍间隔契约；无需改TLS/PN、M1/M3/M4、OuterRepair、内核规则、generation或owned Stop。

- Root App明确15/30数值选择→同一Service Start Intent→原Go CLI `--android-native-health-seconds`→原 `V4LinuxClientProductConfig.HealthKeepaliveSeconds`→真实native Rust Health config/readback。
- 原Service拒绝不支持值，Go默认和旧Java API旧预设为15；原ConnectionSettings和SAF只存整数，不存Native状态。
- 不实现Java/Go心跳、没有按包检查或新计时器。理论上空闲控制包更少，CPU/唤醒/续航收益**NOT_PROVEN**；保留应用数据面与旧Linux/Windows默认语义。

Host JVM用原生产参数构造和实际预设往返，Go源码门检查真正Rust配置链；同源原ARM64/x86 Go/Rust、签名ARM64 APK及Linux原服务器Oracle靠B37 Action逐项给出PASS/FAIL，不把Host成功冒充手机成功。物理App真实TCP/UDP、系统netd DNS/IPv6、Game2/4、切网和热点仍MISSING/NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B37让原Rust M4 HealthClock已存在的15/30秒间隔通过Android原App及Go CLI真实配置，默认不变，不新建安全层或数据路径。"}
```
