# H2202｜用户选定：放弃旧 Admission V1，唯一 V4 加密控制格式

**用户最新授权**：不要求旧版协议互通，不再通过客户端标志选择是否发送控制填充；统一强制新版。不能把“无确定私有前导/固定TLS应用记录长度”夸大成流量分析无法识别。既有[TLS建链唯一契约](../architecture/TLS_HANDSHAKE_CONTRACT.md)与源租户隔离/真证书/Go→Rust owned Stop不变。

## 唯一格式与失败处理

1. 原标准TLS1.3/uTLS成熟实现完成合法ClientHello/证书/Finished校验，且server在原SessionID HMAC识别后再受保护认证用户名/密码。没有ClientHello前私有头、伪TLS扩展、额外TLS握手往返或V3数据面修改。
2. 当前V4 Admission固定24B扩展，仅使用BE16版本`2`、原features、epoch、feedbackPages、GameFec byte21、NormalFec byte22、客户端启动填充 byte23 `0=off,1=tls,2=flows`。任何版本`1`、未知版本、未知模式及矛盾profile立即拒绝，**不支持V1自动识别、不降级、不保留可选`ControlPadded`或旧版无尾部线格式**。本地旧UI bool→新选项属于非网络配置迁移，与旧线格式互通无关。
3. 成功 Admission request与reply **每个**在原TLS ApplicationData写入完整 `24B extension | BE16 length | CSPRNG bytes[32..500]`。off同样随机；长度均匀拒绝采样，32..500每向独立。解析器在Go→Rust Detach之前完全读取2B长度和尾部，超界、截断、随机源失败拒绝，不会把残余消息误当Rust业务帧。原request/reply各只有一次TLs应用发送，不加新的ACK/握手/RTT。
4. 失败也不可退回旧1字节固定TLS ApplicationData：服务端已进入Go TLS后的拒绝状态以 `status byte | BE16 length | CSPRNG 32..500B`单次发出；客户端必须完整消费后才返回实际错误；裸1字节status不被接受。不存在成功回复改档、版本替换或业务FEC能力自动降级。
5. TLS exporter含整个24B固定扩展，绑定version、mode、features与server epoch的冷KDF。认证结果产生不可变cold session snapshot。Linux Normal、FEC Fixed/Auto、Game2/4服务端只按客户端已认证档位设置Rust发送；Game多lane一致、单lane换代不得改档。Windows Normal/Fixed/Auto/Game2/Game4的CLI/WinForms mode现在必须传到相同V4ClientOptions，Windows Game server检查认证同组值，原Windows native Rust/本地GUI冷模式仍按原物理owner约束；缺实际Windows NPF/Wintun签名不可声称真实应用通过。
6. 不修改业务Rust AEAD密文格式、record PN/Seq/FEC parity/repair、TLS ClientHello和任何未授权初始载荷；不声称随机控制内容本身使任何DPI不能识别流量。长度本来就可随TLS分段、SNI/证书、MTU变化，所测的是独立随机控制应用记录长度和不出现项目自造前导，不是“绝对无指纹”。

## 同SOURCE测试

- 原Go真实TLS1.3与受保护账号：三档回显、双向随机长度至少多种、off也随机、V1/未知版本拒绝、恶意模式、长度越界/截断、随机源故障、导出密钥一致、冻结owner篡改拒绝、认证失败完整随机回包；其他V4能力/真实证书反面回归。
- Linux x86_64和真正native aarch64：原Go+Rust/ISA-L每ISA同一bundle，12场每ISA；Normal/Fixed/Auto/Game2/Game4、off/tls/flows，服务器本地CLI故意相反；真TCP/UDP双向kernel、AF_PACKET padding、MTU/TUN/IPv6/Stop；不刷H2201旧SOURCE成果冒充新SOURCE。
- Windows2025：原Go V4 TLS协议真实原生单测，构建当前Rust DLL + 原Go Wintun/NPF入口 + WinForms真实配置与CLI check-config。**只有原生系统构建/配置，不代表新源码真实Windows NPF/Wintun双端包、GUI按钮→网络一体化测试**；若CI或runner支持另行资格。
- OpenWrt aarch64 musl Rust engine、Android arm64 NDK Rust engine＋Kotlin VpnService Gradle仅交叉/编译，真实OpenWrt路由器、Android实体VPN/插件JNI联通与Stop不具备，不冒称原生网络验收。未接线的macOS/iOS不假造测试。
- 仅已完成jobs+原ZIP/manifest SHA签名且治理通过才能把新SOURCE相关平台升级为PASS；未测试机型/失败历史逐项记录，完整PLAN029技术出口仍OPEN、PLAN030不开。
