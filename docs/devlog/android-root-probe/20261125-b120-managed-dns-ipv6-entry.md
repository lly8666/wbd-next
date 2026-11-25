# B120｜统一 DNS 与 Windows IPv4-only 入口

用户确认 B118 实机正常，前次 ROOT_LAUNCH_FAILED 原因为未开启 Root 权限。选择 B118 的选定下游上行挂钩，BPF/HAL/IPv4 tether owner 不再改动。用户报告 CN 普通分流热点 IP 正常、域名失败；旧下游 IPv6 DNS 依赖 SIT，系统/TCP DNS 独立开关；是明确覆盖缺口，不断言唯一实机根因。

参照 main PLAN029B：三个互斥 DNS 模式、两上游，APK 普通 DNS 自动使用原 IPv4/IPv6 UID UDP/TCP53 入口，选定 UID 不依赖特定 socket mark；默认 AAAA 本地 NOERROR/NODATA，A 不变、无 FakeIP，Private DNS/DoH 不接管。共享 IPv4 继续原 DNAT relay，IPv6 DNS 使用同一 resolver + 选定 downstream 实际地址（含 link-local）与原 journal NAT。IPv6 业务使用现有 UID/下游 FIB 进入自有 TUN 后原 IPv4 入口拒绝；IPv4 TUN MTU <1280 使用同表 blackhole，不提高 MTU。保留既有显式 SIT 高级兼容。无全局 IPv6、物理网卡、系统 DNS、协议或 BPF 变更；复用现有 DNS relay。Normal IPv6 消费后继续有界 burst，Game 原入口已检查 IPv4。Host 新测试真实 UDP/TCP4/6 AAAA、实际 netlink 任意mark DNS6、实际TUN IPv6入包与低MTU回收。新 SOURCE CI/实体待验；热点真实端到端未验。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Unified managed DNS choices, selected UID port53, local AAAA and default scoped IPv6 entry drop; preserve B118 sharing."}
```
