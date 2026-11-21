# B21｜Root App 按需查看已有原 Rust M4 TUN/RAW/TCP/UDP 真实收据

基线 SOURCE `162d56706df926891526eda723430d3152c9b928`。Root App原有 DNS 诊断和 NATIVE_READY，但原Rust M4的实际TUN入站、RAW复制、下行M3认证、逆向TUN写回等已按4s节奏写入现有App私有有界数字收据，却未接到可见UI。实体设备受限时，它能区分Start授权和内核业务真的流经原M4的阶段。

- 新正式纯Java `RootM4TrafficBrief`：只读取 `RootDiagnosticReport.build` 已校验的 `native_m4_numeric_debug_samples` 中的 `kind=m4`，再经 `RootDiagnosticReceipt.safeNativeSnapshot` 验证当前真实字段格式；显示TUN总入站、TCP/UDP、RAW copied、M3 authenticated、逆向TUN已写六组数字，不显示 `kind=rx` 里的 IP/端口或用户/密钥/正文。
- `RootClientActivity` 新增“查看最近原生M4 TCP/UDP内核收发”按钮。**只在点击时读取本APK原有诊断文件**，没有额外Root、网络、Go/CGo/Java数据面、JNI poll或内核读线程。原1s status、4s Go/M4 snapshot保持不变。
- UI精确说“最近一次数字收据，可能来自已结束会话；不是应用E2E、Fixed/Auto APPLIED或性能达标”，防止静态/历史日志充当前手机的已通过证明。
- 原Root App Host门编译并执行正式生产Parser的真实M4字段顺序测试：取最新合法样本、只提取指定数字、添加额外不受支持字段拒绝、没有样本返回NOT_OBSERVED。App/Host/签名APK一律按冻结SOURCE验收；不触发实机/服务器网络测试。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B21 Root App on-demand real original M4 TUN/RAW/authenticated reverse counters from existing numeric receipts, no additional steady poll or packet owner"}
```
