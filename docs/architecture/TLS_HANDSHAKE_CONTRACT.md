# TLS建链唯一契约｜2026-11-04用户红线

适用于首次连接、每条Game lane、轮换、休眠唤醒、切网重建及Windows/Linux/ARM64的实际产品入口。用户已明确允许预共享route-key，**配置便利不得突破标准建链流程及报文外观**。本契约覆盖PLAN028及后续计划；稳态无HOL数据面仍沿既有TLS-like设计，不把它冒称完整标准TLS流。

## 1. 不可突破的边界

- TCP建立后，客户端首段有效载荷必须开始标准TLS ClientHello；服务端在收到ClientHello前不得发送应用载荷。禁止项目私有前导、固定magic、裸公钥/挑战交换、额外协商往返；也禁止把私有前导换成随机长度、伪TLS头、假CCS、假HRR或伪装成TLS扩展继续发送。
- ClientHello/ServerHello/Finished及证书握手由成熟TLS实现生成和校验，扩展、长度、状态顺序、兼容CCS及票据均须符合所用TLS版本。协商未实现的ALPN协议来装作HTTP不可接受；不自行拼接证书签名/Finished，不删除身份验证来过门。
- “无特征红线”的可执行含义是**零项目私有建链前导/字段/流程偏差，保留标准握手的包长生成规则**。packet长度随SNI、证书链、MTU、TCP分段正常变化；不规定固定包数，不用无条件随机填充制造新的指纹。TLS record与TCP segment不是一一对应。
- 标准握手合法性和指定网站指纹相似性分别记证据，不能用“TLS成功”或“解析器未报警”代替外观审计，也不能承诺任意DPI无法识别。该证据边界不授权放宽上述红线。当前本地配置证书、未选择ALPN等实际行为须如实登记；自签证书不能冒称第三方网站真实身份。

## 2. 已选最小方案：预共享route-key，复用原SessionID识别

1. 服务端生成并持久保存32字节随机key；客户端通过连接配置导入或显式填写。已有合法显式key兼容保留，生产不使用公开常量。无key时本地报配置缺失，**不打开连接做自动协商/隐式回退**。随机生成/导出/帮助与适用GUI/参数目录须同步落实；日志不输出key。
2. server级key可以由多个账号/设备/lane共用，它仅用于入口识别，不替代TLS服务器身份验证、TLS内用户名密码认证、会话/IP隔离。无需逐用户试key、额外key ID、线上密钥发现或新轮换协议。
3. 直接复用旧`hello.go:markerFor`和`tls.go:newFirefox120Client`：CSPRNG生成ClientHello.random，既有HMAC-SHA256(label || random || normalized SNI)结果占用原本32B兼容SessionID。标签只是本地HMAC输入，不明文发送；不增加字段、扩展、record或往返。实际TLS库保持SessionID回显和HRR等合法状态；不得把同一个固定token作为每次SessionID。
4. 这不是TLS `pre_shared_key` 扩展/PSK握手：保持真实完整证书握手，不因此省略Certificate/CertificateVerify，也不引入0-RTT。后续账号、安装标识、IP、模式、MTU等沿既有TLS保护的Admission交换；Rust稳态record/AEAD/PN/FEC/重传及generation不变。
5. 证书验证独立于route-key来源：修掉只在空key/自动分支才设置`VerifyServer=true`的耦合。使用受信任证书链或显式配置的该服务器证书/公钥固定校验；自签材料按应用专属信任导入，不静默关闭检查或安装全系统信任。先完成服务器身份验证，再发送密码。
6. 普通未识别ClientHello/错key沿项目既有合法回落或关闭策略处理，不能发私有challenge/错误magic。核查实际入口，不把旧仓库有fallback当成当前已接通；缺失处记录并最小接线，不另造通用前置代理。

标准依据：[RFC8446 §4.1.2](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.1.2)允许兼容SessionID为新的32字节不可预测值；[§4.4.3](https://www.rfc-editor.org/rfc/rfc8446.html#section-4.4.3)要求真实证书私钥签名验证。只拥有借站公开证书不能替代其私钥。

## 3. 当前修复包与顺序

**优先于继续PLAN028切网/性能扩测。**先收存已在途结果，不取消其他有效修复或回退整条主线。

- 移除产品`v4_route_prelude.go`的自动入口及双方调用，配置解析/装配/帮助/夹具同步要求预置材料。复用显式key路径；不恢复无证书验证的旧默认，不回退近期多客户端/Stop/切网修复。
- H1048的`WB-R1`、每向37B、server先发的X25519方案**已被用户明确否决**。原H1048/H1049/H1052/H1057等SOURCE的功能、认证、ARM原生结果保留为原范围事实；该路径握手外观不合格，不能被功能PASS升级。修复尚未实现/测试时明确OPEN。
- 同一批写齐公共冷入口、Windows/Linux调用与装配、配置/CLI/GUI适用项、功能卡及夹具，再冻结SOURCE。不得夹带FEC/Game算法、稳态wire、route-key在线自动发现或长期双协议开发。

## 4. 有限而直接的验收

1. **字段与状态**：正常/缺失/错误key、正确/错误密码、可信/不可信证书；每次SessionID变化且原32B长度/合法回显；不能在证书拒绝后发送密码。缺key应本地失败、不发探测包。必要HRR/TCP拆包用已有TLS测试接口覆盖，不要求公网恰好触发。
2. **真实线上握手审计**：从SYN开始有界抓取并重组两个方向，验证首载荷为client ClientHello、server无提前载荷、无TLS外前导、无新增握手record/往返、TLS长度/扩展/顺序有效。与同版本uTLS/Go TLS、同SNI/证书/MTU配置的基线比对可变字段以外的结构和record长度；不能拿固定200–550B或固定IP包数当标准。证书/Finished需要验证时仅在隔离夹具临时导出测试密钥并在job内解析，完成后删除，artifact仅留脱敏摘要/hash/失败原因。
3. **模式和平台**：复用既有7模式短功能夹具，验证真实TLS→认证→Rust业务/Stop；Game每条lane及一次轮换/重连都检查相同契约。Windows实际入口补同源代表；Linux按当前用户约定整任务x86/x86、下一个ARM/ARM轮换，真实ARM运行不可由交叉编译/QEMU替代。可复用同源码二进制，不为此重刷全部弱网/长测矩阵；未覆盖平台或模式明确NOT_RUN。
4. **效率**：一Action一场景/一个测试控制进程，场景所需双端/多client不算并行压测；独立Actions可并行。一次构建按SOURCE/平台/manifest/hash复用。报告冷握手耗时、方向/record长度摘要、真实业务和Stop；不存在热路径变更时不强制全吞吐A/B。
5. **退出**：被修正入口无前导、标准TLS握手与服务器验证成功、必要反面用例和平台/模式证据齐、配置/帮助/功能卡一致。旧自动路径不再可达，不保留隐式降级。然后续PLAN028 cursor中原切网/交接任务；未完成不能因一条Action绿灯宣称完成。
