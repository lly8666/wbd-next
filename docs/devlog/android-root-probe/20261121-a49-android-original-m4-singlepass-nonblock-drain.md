# A49｜A48真机双向已通后的Android原M4热路径减负

## 实证起点（不假称速度提升）

2026-11-21 用户自行提交 A48 SOURCE `4a19f20456e74f3e7700e3a2876eda40536bb8d9` 的 API36 Safe TXT（82固定事件、44组原Rust原生数值）：Normal/off、选定普通App IPv4 UID；原 Go SYN/SYNACK/TLS/受保护Admission、/32 OS读回、Rust M4/UID读回、owned Stop EXIT0；原 M4最终 `read=1243,data=1229,auth=1227,rawtx=887,tun=887,rtun=1218,rejected=2,writefail=0`。真实原Rust收到并认证服务器方向密文，写回真实Android TUN；用户报告“数据通了，性能一般”。但 APK证书验证实际 DISABLED，TXT无应用层逐字节确认、吞吐、RTT、丢包或CPU比较，故不能宣称完整安全E2E或网络性能合格。旧A47的 `auth=0/rtun=0` 不能作为现行阻塞。

## 本次仅改两个确定性热路径冗余

1. 原 `AndroidBoundRawRx::read_original_record` 的 A48 逻辑对几乎所有真实DATA先遍历 TCP payload算 checksum（本机全数不匹配），再从头解析第二遍进入原M3。A48严格成功与checksum-only失败后宽松成功的**接受集合**恰等于既有 `parse_data_packet_android_m3_pending`；Android直接单遍调用它，全部 IPv4/IP-checksum/tuple/flags/MTU/分片/选项门不变。保留原 M1 seq 和 M3 AEAD/unique PN/replay决定最终认证。仅1/128已接受DATA在诊断侧抽样调用严格parser，因此 `tcpck` 为抽验中的失败**样本数**，不可与A48旧版逐包完整统计相除当“修好checksum”。Linux/Windows正式 strict parser不改。
2. Android真实 TUN fd在 `adopt` 已明确设为 O_NONBLOCK，RAW RX socket也为 SOCK_NONBLOCK。原两个M4 worker 在一次 poll 叫醒后，每个后续包额外 `poll(0)`；改为最多8次直接 `readv/recvfrom`，EAGAIN正常结束当前批次、无额外error计数。其它IO错误仍原 fail路径；不改 AEAD密文、wire、租约/Scope读回、generation、Health或Stop和线程数量。

## 验证与下一步唯一门

加入真实Rust Host测试 `a49_single_pass_matches_a48_two_pass_android_admission` 对原写包的合法、仅TCP checksum损坏、IP checksum损坏、四元组、flags负例逐项核A48旧接受集合和A49单遍结果相等；A48老测试及main H2216 TTL保持。Android ARM64/x86 CI-only原Go+Rust、正式签名ARM64 APK、原Linux Go/Rust Normal/off Oracle与源锁检查只须同 SOURCE 一次。Host/构建 PASS 仅能证明代码边界，不产生CPU/吞吐PASS。

下一份最有价值的证据是**相同手机/服务器/物理网络** A48旧签名APK与 A49新签名APK短时顺序A/B：少量相同大小的TCP下载与上传、UDP双向/ICMP RTT、最大净速Mbps和p50/p95、进程CPU或原有M4 thread cpu_ns、两个来源的原Rust M4计数/Stop；没有实际A/B只报告 `PERF_NOT_PROVEN`。不提前增加DNS全局拦截、固定/自动/Game模式和新防御框架，不操作未单独授权实体设备/个人服务器。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A48 API36真机证明原Rust auth1227/rtun1218后发现性能问题，A49只对Android原M4删除A48重复验TCP校验和/双遍解析以及每包多余poll0，保留1/128真实采样、原M3/PN/Stop与Linux/Windows严格parser；同源回归，吞吐待真实A/B。"}
```
