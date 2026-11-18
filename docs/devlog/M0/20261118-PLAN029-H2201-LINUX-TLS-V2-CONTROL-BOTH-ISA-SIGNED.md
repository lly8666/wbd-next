# H2201｜Linux V4 TLS1.3 加密配置请求/确认各随机变长，按客户端控制服务器：双ISA 24/24 真原生 PASS_SCOPED

新冻结产品/夹具 SOURCE `ee69bc68127af725f642520108664af6bba31f7f`，[原生 Action 44304946337](https://github.com/lly8666/wbd-next/actions/runs/44304946337) **completed SUCCESS**。native Linux x86_64 和 aarch64 两个独立 Job：每 ISA 五模式 (Normal/Fixed/Auto/Game2/Game4) 的 tls/flows 及 Normal/Game4 的 off，共12个真实 client/server OS netns 场；合计 **24/24 PASS_SCOPED**。

与H2197服务端本地 CLI 同步测试不同，这次每场强制 SERVER CLI 与CLIENT CLI 相反：客户端 off 时服务端配置 flows，但真实 Rust M4 双端发送填充都是 0；客户端 tls/flows 时服务端进程配置 off，真实 AF_PACKET copied 双端对应客户端档且字节>0。原Go TLS1.3 protected Admission V2 的 client mode/version 回显，KDF exporter 绑定，随机BE16+32..500B request/reply各自处理，测试涵盖真实证书和账号、三档/错误长度/截断/旧V1/随机熵故障、会话cold不可变。每真实场双向kernel TCP/UDP、owned IPv6/TUN/MTU、两个原Rust Stop和netns清理通过，Game fixed6源语义保留；**这证明受保护配置驱动服务端，不是单纯CLI参数或者help假通过**。

原始x86 ZIP artifact 14428385766 SHA `7ff6d38e`（234成员CRC PASS）、ARM ZIP artifact14427977024 SHA `69878fcb`（234成员CRC PASS），summary hashes、三个实际二进制SHA、24场双端每方padded_record与bytes完整在[原签名证据](../evidence/M0/PLAN029-H2200-LINUX-TLS-V2-CONTROL-CLIENT-SYNC-X86-ARM64-TWENTYFOUR-REAL-PASS-20261118.json)及GitHub Action原ZIP。示例x86 normal tls: client2条425B、server2条101B；fixed tls:718/296B；game2 fixed6 flows:1380/1733B。ARM64 normal tls:566/918B，game4 fixed6 tls:1316/2042B；两ISA原V2 off双端0B。流量分析本身不能证明完全不可识别，真实TLS密文capture并未独立测试，勿夸大。

历史红CI明确保留：初版SOURCE a22ab7 [44303725701](https://github.com/lly8666/wbd-next/actions/runs/44303725701) 旧静态断言与新role loop文字不匹配；第二版 e36248 [44304050978](https://github.com/lly8666/wbd-next/actions/runs/44304050978) 新纯 Go TLS 测试误挂native tag而被旧raw测试缺助手符号阻断，均在网络运行前FAIL。冻结SOURCE ee69bc后分离不带native-tag Go TLS 协议测试、仍原 native Go/Rust二进制和测试、实际24/24 SUCCESS；中间失败不能改写历史。

不强行覆盖 V1 老二进制互通、默认shared443多用户异档并发、auto-IP OS动态物理MTU、真实DPI/应用TLS、实体ARM/跨ISA及性能等未验边界。PLAN029 日用限域PASS_SCOPED，完整技术出口OPEN，PLAN030未启动。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"H2201 new native source ee69bc68 x86/ARM 12 scenarios each: original Go TLS1.3 V4 V2 bounded variable encrypted control request/reply; verified client off/tls/flows drives actual opposite-CLI Linux server Rust M4 copies, 24/24 PASS_SCOPED. Legacy V1 grammar-only and other exclusions retained."}
```
