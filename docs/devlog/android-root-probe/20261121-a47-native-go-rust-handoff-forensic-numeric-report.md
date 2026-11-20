# A47｜Go→Rust 正向真实交接证明，反向 RAW/M3 逐层数值诊断

## 实机 SOURCE 与事实

用户 API36 SOURCE `1b20ab1d36cf1bf6c79c564e9b6340118ec9c33c` 真机 78 条安全阶段，选定应用模式。原始 FakeTCP SYN/SYNACK、标准 Go TLS（用户这次服务端证书验证关闭）、protected admission、受保护/32 kernel readback、原Rust RAW/TUN attach、M4启动、Go RX旧FD kernel BPF零丢弃、UID真实规则及读回均成功。之后原Rust **真正从选定APP源发出** TUN_TCP、TUN_ICMP、TUN_UDP（因时间不同）、实际原 M3业务RAW sendto copied；这已经是Go提交所有必要原 Rust TX元数据、唯一Rust worker操作真实内核的证据，不是单纯UI READY。仍无原 Rust 的`RAW_PARSED`、`RAW_AUTHENTICATED`、`APP_REVERSE_TUN_WRITTEN`。`RAW_SOCKET_READABLE`和`RAW_PARSE_FAILED`先于用户业务发生，不能按时间推断这个包是后续业务回包。用户报告公网服务器与Windows客户端原业务长期正常，不应默认归咎其公网NAT。

## 真实旧逻辑盲点与本次改变

A46b 已逐字节同步main已通过的H2216 DATA/ACK TTL修复。本次在Android原Rust Bionic`AndroidBoundRawRx::read_original_record`及其唯一原始`recvfrom`调用位置，新增22个无锁Atomic的只读类别和**真实最近一次 IPv4/TCP 头样本**：内核read成功、DATA解析通过、合法纯ACK识别（**不会冒充数据**）、四元组不符、IP/TCP checksum不符、TCP flags、长度或分片、options、TTL zero、other、sequence extension拒绝、原M3 owner offer拒绝、recv errno及最近真实长度/TTL/flags/src/dst IP/src/dst port。真正`RX_SEQ_BAD`及`RX_OWNER_OFFER_BAD`分别在原Rust M1/M3 seq extension和实际`offer_after_active`拒绝点计数。没有更改这些门的返回值；原 M3 AEAD、PN/replay、original TLS、BPF FDs保持不变，也不会引入第二个 TUN reader。**注意**：src/dst IP以uint32打印为十进制而不是人类点分IPv4；可以离线转换。用户明确要求优先诊断、无需匿名，但源码仍不输出凭据/密钥/正文。

新增只读Rust FFI `wbd_m0_embedded_go_loop_raw_rx_debug` 暴露22字段，Go原有低频 `OriginalLoopPulse`读取；每4秒发两个纯数字模板：
`V4_PUBLIC_ANDROID_M4_DIAG role=client kind=rx ...`（22项原RAW socket快照）及`kind=m4 ...`（18项Rust原worker真实TUN/RAW/M3/回程累计、rx/tx error、Health）。Stop前再捕获一次。不新增RPC、Go每包操作或Rust热路径日志。RootClientService仅接收两种固定前缀并交给**精确字段/字段顺序/仅数字** allowlist，App私有0600有界收据保留原阶段枚举和增加`native_m4_numeric_debug_samples`段；不允许其它root stdout、凭证或任意日志混入。Java Host测试验证实数获准、其它字段/秘密被拒；原 Go Host测试验证完整计数/真实头样本数值映射；ARM64同源原Go+Rust构建与ELF symbol/AAPK均必须PASS。

## 下一次高价值的解释，不假设PASS

- `kind=rx read=...` 始终不增加而 `kind=m4 rawtx`不断增加，关注服务器收到客户端Rust的真实外层M3、服务端是否有回包、Android网络RAW socket BPF、下行是否被物理链路吞掉；不能仅凭这些证明某一端故障。
- `kind=rx ack`增加而`data=0`：原Rust只读到了纯ACK，不代表丢了业务；此前`RAW_PARSE_FAILED`很可能来自ACK。
- `tuple/ipck/tcpck/flags/len/opts/ttl0/other`开始增加：可区分各个严格内核报文门，先与main Windows行为对齐，再决定针对性真实修复，不盲目删除校验。
- `data>0`但`seq`或`offer`增加：Go→Rust真实序号锚/原M3 owner接线方向，修相关原函数。
- `data>0`且`seq=offer=0`但`kind=m4 auth=0,rejected>0`：原 Rust AEAD/PN/replay或入站记录，不关闭这些验证。
- `auth>0`而`rtun=0`：原Rust reassembly / inner leased IPv4、TUN写回；继续排查。
- `rtun>0`且Chrome或ICMP仍不通：检查选定UID、Android netd、真实TCP、DNS。原服务端已证Windows业务，不要求用户改server。

本次不宣称手机已经正常联网；绝不可把真实Kernel RAW复制冒称服务器收到，也不把原Go成功TLS冒充Rust反向AEAD完成。当前仍选定普通App IPv4，不扩大到全局；root owned Stop继续受原流程管理。此前各SOURCE/Actions FAIL与PASS原封保留；本次真实Actions须验证签名APK同源后才交用户。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A46b真机Go到Rust真实TUN/RAW发送已证但无反向数据；A47在原Rust同一RAW FD和M3 seq/offer位置增加22项真实数值分段诊断，经原Go低频状态和App有界数字收据导出，不放松AEAD/PN/Stop。"}
```
