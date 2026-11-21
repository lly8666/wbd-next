# A40｜真机两次TLS及保护Admission完全成功，进入原Rust/OS租约后置排障

用户提供 SOURCE `d897e7f273bbc385a34f436797fe09a50d639939` Android API36 固定93事件、两次真实Start。两次均原Root Go TUN、RST guard、FakeTCP Established、完整TLS（关闭证书身份校验）、Original Protected Request Write、Reply Parsed及 `ORIGINAL_GO_ADMISSION_VERIFIED`；第一次后139ms、第二次后142ms 原Go Exit1，原RST Guard MATCHED_RST_DROP / STOP_CLEARED、OWNER_CLEANUP_FINISHED。这充分证明原受保护认证真实通过，但不证明OS /32地址、Rust M4或UID路由与App真实业务；原报告 `PROTECTED_ADMISSION_VERIFIED_LEASE_UNPROVEN` 不能定位退出。

真实 `EstablishClientV4` 发AdmissionVerified后，原 `V4LinuxClientProduct.ConnectAuthenticatedPeer` 尚须真实ColdSnapshot、原FakeTCP.Detach、原Go→Rust C ABI Prepare+Commit、验证服务端保护/32 lease字段、真实 `ip addr add/del/-j addr` 内核读回、原Rust绑定租约、MTU、Android物理network handle+MTU绑定、原AF_PACKET/TUN attach、Health与Rust loop，之后才调用UID private FIB规则。A40直接在每一个原真实函数完成或错误返回路径标记29个固定 POSTAUTH 原生阶段；Android CGo RustPrepare/Commit失败使用已有typed Rust错误来源。Java RootService只匹配固定原Go日志锚，不传任何用户秘密；RootDiagnosticReport最后失败阶段优先于旧AdmissionVerified，新增JVM负例循环对全部19种失败和3个通过中间阶段进行回归。API36真实失败原因仍待用户自行安装A40并运行，绝不编造。

A40仅在实验分支变更；不更换原Go/TLS、受保护认证、原Rust M4或UID路由内核owner。下次在Android仅选一个普通App UID Normal/off做一次有界Start，看 `ORIGINAL_GO_POSTAUTH_*_FAILED`（尤其NATIVE_PREPARE、NATIVE_COMMIT、LEASE_ADD/DEL/READBACK、UNDERLAY），再直接修对应真实问题。原Linux真实Normal/off Oracle与签名APK同SRC CI是Host质量门，不等于Android实体手机业务已通。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A40 Android真机TLS+protected admission 2/2 PASS但139ms后原Go exit1，增加原RustPrepare/Commit、/32内核租约、Android物理绑定和M4真正失败阶段，原协议不变。"}
```
