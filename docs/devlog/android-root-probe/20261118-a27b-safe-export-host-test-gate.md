# A27b｜修正脱敏报告 Host 单测漏接的验收门

A27 同源 [Action #44296125095](https://github.com/lly8666/wbd-next/actions/runs/44296125095) 最终 SUCCESS（11 SUCCESS / 4 SKIPPED）；原 Go rootjournal 全App /32 throw、防误入TUN、v3→v4恢复、撤销、原 ARM64 Bionic Go/Rust、正式 APK 与 DEX 构建验收通过；KSU、TAP 和 Android guest 均跳过，真机未跑。审查 root-arm64-app 官方日志发现：新增 RootDiagnosticReport 进入签名 APK、编译正常，但 ci/test-network-scope-gate.sh 中实际漏调 RootDiagnosticReportTest；**A27不能把过滤器正反测试宣称 PASS**，此前 A27 成功仅可报告构建、签名/类存在/原Go路由测试。

A27b 最小修正是让正式 APK Host JVM 前置 Job 编译并真实运行生产同一 RootDiagnosticReport 与独立 RootDiagnosticReportTest，覆盖恶意插入 IP/账号/密钥的行严格丢弃、只允许固定枚举、SYN sendto≠SYNACK、路由私有表读回≠netd物理路由、Stop 未 join、滚动前后收据。若修正新 SOURCE 通过才报告报表导出 HOST PASS。无新增设备操作、模拟网络、产品TLS/MTU变更，保留历史 scoped 状态、Draft PR与用户范围。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"审计发现安全导出器虽进签名APK但遗漏独立Host JVM真单测，补接唯一生产报告类正反例与单独验收门，不虚报此前PASS。"}
```
