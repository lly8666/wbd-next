# H2200｜V4 原 TLS1.3 加密 Admission V2：客户端填充选择及控制长度随机化

## 决策与威胁边界

严格遵守 `docs/architecture/TLS_HANDSHAKE_CONTRACT.md`：绝不修改/伪造 TLS ClientHello、ServerHello、Finished、SessionID 或 TLS 扩展；不添加握手前导/额外往返。只在**证书验证后的原 TLS ApplicationData** 中对原 V4 Admission 请求、成功确认消息增加有界随机尾部，防止其加密应用负载长度恒定。无法据此承诺任何 DPI 不可识别；握手指纹、证书/SNI、连接时序、认证失败短响应及外层长度分布仍可被观察。拒绝随机尾部的解析错误不得静默走旧协议。

## 严格版本化语法

- 保留原 V4 基础 request/reply 和末尾 24B 扩展长度不变；扩展 [0:2] big-endian version：`1`为历史常量控制格式、`2`为本次保护控制。version1 的最后 byte23 必须为0、没有尾部、启动填充严格off；原版本1来源的key派生语法不变。
- version2 扩展 byte23：`0=off, 1=tls, 2=flows`，只允许0..2。原 byte21 Game fixed 与 byte22 Normal fixed profile 不变，feature位不扩权。每个 request/reply 的 24B 扩展之后，仍在相同 TLS 加密应用消息内附加 `BE16 pad_length | random_bytes[pad_length]`；`pad_length` 均匀从32..500字节随机取，字节使用`crypto/rand.Reader`，每向独立生成；协议无随机填充内容语义。
- Reader 先按现有精确头、账号/policy 和24B扩展取值，再按所解版本读取2B长度及其字节；界外、截断、额外未知版本拒绝，绝不把尾部留给 Rust M4/early DATA。每向仍只一次原TLS `writeFull` 与一次相反方向回复，**不增1个应用往返**。CSPRNG失败连接前或构包时直接失败。单方向新增34..502字节，除现有TCP/MTU规则不引入新热路径写包。
- Client 使用自己的本地 `StartupPaddingMode` 构造version2请求；Server必须先确认TLS1.3、密码/用户、受保护FEC/Game策略及epoch owner，再在同version2回包中原样确认byte23；Client拒绝改档、version退回或feature/epoch变更。原 `v4DeriveRecordKeys` 的TLS exporter上下文包含完整24B扩展，绑定版本+档位（随机无语义尾部不参与KDF）。Server对**当前且仅当前会话**的验证档位生成不可变cold snapshot，传给原Rust M4冷配置；服务端进程级 `--startup-padding`不再决定该客户端；多租户共享 server 每个owner独立。
- Game2/4的每条TLS lane须提供同一客户端档位；组Commit前核对全组一致，单lane换代必须与存量组一致，否则拒绝，不重置FEC、PN、加密key或发新的网络控制消息。旧客户端version1可连接新服务端且其填充为off；新客户端version2遇旧服务端会明确拒绝，**不执行静默回退**，需同步升级对端。服务端原CLI接受旧参数但不覆盖受保护客户端选择。

## 测试门与安全范围

- 原Go单元：V1原字节稳定与未知version、恶意byte23、长度<32 / >500 / 截断、熵失败；V2两向随机长度与精确消费（不得残余早期字节）；原TLS1.3真实证书验证、off/tls/flows回显和不可变cold篡改拒绝。
- 原生Linux每ISA一个SOURCE锁定原Go+Rust/ISA-L bundle；12场/ISA：五模式tls/flows与Normal、Game4的off，服务端CLI故意相反；必须观测两端实际Rust M4 AF_PACKET字节、真kernel双向TCP/UDP、owned TUN/IPv6/MTU与Stop，随机控制消息单测与真TLS共证；一Action失败不兜底变PASS。
- Windows WinForms及完整跨版本/跨平台交互、物理ARM/实体公网DPI/真实站点指纹、小TCP p99、长期CPU/弱网FEC恢复不在此SOURCE资格范围；记录NOT_RUN。保留PLAN029旧SOURCE限域PASS和历史FAIL，不宣称完整技术收口。
