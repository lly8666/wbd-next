# B7｜Android 原 M4 物理 DNS 重传复用、App 原位收据与只读真机验收

起点：B6 SOURCE `15cc75616387e2b564c9ae6a85376d12f8f1bb32`；Android 产品 11 SUCCESS/4 SKIPPED、功能卡治理成功。用户希望继续完成功能卡全部功能。此次只修改可真实进入 Android Normal/off 原生链路的内容，不用 UI 假开关冒充 Fixed/Auto/Game 已可用。

## 1. 原 Rust M4 物理 UDP DNS 丢包重试

原 `PhysicalDnsUdpFlows::prepare` 每次收到同一普通 App UDP53 查询的重传，都占一个新 synthetic ID/64 槽，即使前一个物理请求还在等回包。现在只对原 5 元组相关身份和相同 DNS ID/QNAME/QTYPE/QCLASS 的**未到期同一问答**，重复使用已拥有的 synthetic ID 和同一反向映射；不同 App、解析器、问题不共享。重试仍通过同一物理 Network/UDP socket 每次真实发送。API 现在额外给出 `new_slot`：物理 sendto 失败只取消本次新建槽；重传失败保留此前原有效请求映射。原 12s TTL、内存上限、收到有效回包后的单次逆映射、owner generation 和 Stop 仍原样。没有另一个 TUN reader、Go/JNI 逐包、DNS 兜底或强制 TLS。

新增两个真实 Rust IPv4 Host 例：同 App 连续多次重试、不同 App 原端口隔离、重复发送失败不销毁旧请求、12s 超期后新 ID 分配、合法回答恢复 App 原地址/端口、重复回包和 Stop 后旧回包不准投递。由 `dns-b2c2b-rust-udp-map-host.sh` 同一 SOURCE 执行且源码门检查。

## 2. App 原位 DNS 状态查看

`RootClientActivity.java` 增加「查看本会话DNS收发」按钮，调用纯本地 `RootDiagnosticReport.build` 和新 `RootDNSStatusBrief.fromReport`，只显示隧道/物理收发、CN8503 冷授权、CN/非 CN 路由、TCP53 原 M3 RAW、TC TUN、netd 未接管等固定状态。没有触发 Root、外部 DNS、netd、更改默认，旧用户仍可选择导出安全 TXT。Host Java 证明当前 session 及非法/包含私密信息的状态不泄露。

## 3. 操作员手动的只读 Android 真机证据

原 `android/root-app/ci/device_first_run.py` 仍须用户自行授权运行并手动在签名 APK Start/Stop；新增允许的固定 WBD_ROOT_DIAG DNS 事件以及 `OBSERVED/NOT_OBSERVED/FAILED` 的 CN 物理 UDP send、非CN M3 RAW、物理/隧道逆映射 TUN、TCP53 原 RAW 与 TC1 TUN 写回、双路径冷状态。**不**声称这些计数就是网页 DNS 解析成功、系统 netd DNS 被捕获、TCP53 物理转发或手机端 RTT/吞吐。Python Host 新用例排除非允许事件和只有部分证据的伪阳性。未授权不操作实体手机或服务器。

## 尚未完工的功能卡项

Android Normal Fixed/Auto/Game2/Game4 的真正原 Rust FEC2/M2/Game 发送/接收端口仍主要为 Linux-only，不得用伪接口放行；内层 IPv6、Android 系统 resolver/netd、物理 TCP53 重试、热点/USB/CLAT、真 App UDP+TCP E2E 和性能/切网实测亦尚缺源代码或授权设备证据。后续按真实产品数据路径实施并独立验收。TLS 验证默认 OFF、隧道 DNS 默认 ON，其余 DNS 模式默认 OFF，旧 A47/B3d/B4/B6 收据不更改。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B7原Rust M4物理DNS丢包重传复用同一64槽及真发送失败时保留旧映射；新增App当前会话只读DNS状态按钮、原手机手动检测固定收据与Rust/Java/Python回归，不改变兼容默认、旧ABI及原单TUN路径。"}
```
