# H2204｜唯一加密 Admission V4 扩展 v2

本规范取代[H2200历史决策](M0-PLAN029-H2200-PROTECTED-ADMISSION-PADDING-V2-20261118.md)的v1兼容条款。原Go标准TLS1.3 ClientHello/ServerHello/Finished、证书/route-key安全边界保持；Rust业务PN/AEAD/FEC和Stop不变。**无法保证无流量特征或绝对不可被DPI识别**。

唯一V4扩展24B、BE16版本恒为2、byte23客户端选择 `off=0,tls=1,flows=2`；v1或未知版本拒绝，不回退。加密请求、成功确认及失败回复各独立 `BE16 padLen | crypto/rand[32..500B]`；**off档也有随机控制填充**。任何截断、越界或熵失败都拒绝，Go在Detach原Rust前必须消费所有尾部；无TLS前私有前导或额外应用往返。认证后Server原样回显客户端档位并入原TLS exporter密钥上下文，按per-owner verified cold snapshot安装Rust；服务端本地CLI不覆盖客户端。Game2/4多lane必须同档，FEC不填parity/repair。

Linux x86_64/aarch64各12场真双端24/24原内核TCP/UDP/TUN/Stop [原Action44311389695](https://github.com/lly8666/wbd-next/actions/runs/44311389695) PASS_SCOPED。Windows2025/Linux x86/ARM原 Go TLS [44311389786](https://github.com/lly8666/wbd-next/actions/runs/44311389786) PASS；Android APK/NDK及OpenWrt musl [44311389808](https://github.com/lly8666/wbd-next/actions/runs/44311389808)仅BUILD_PASS。H2203 SHA 3f28e3 额外原GoTLS、WinGo/Rust、LinuxRust及cold装配成功；参见[证据](../evidence/M0/PLAN029-H2202-ONE-V2-LINUX-WINDOWS-ANDROID-OPENWRT-SCOPED-20261118.json)。Windows真设备、实体Android/OpenWrt、跨ISA及DPI/p99尚NOT_RUN；029技术仍OPEN。
