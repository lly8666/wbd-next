# B2c2a：原Rust M4唯一 TUN 读点的 DNS53 线报文透明资格门（2026-11-17）

分支 `experiment/android-temp-root-probe`，基线 `f8a54d5beee9fbc694dede33663e095545951910`；Draft PR #36。禁止独立开TUN fd/read loop、Go/Java逐包泵、FakeIP/VpnService、新TLS/协议、main/M0变更和真机操作。

## 原生 M4 施工

原Android ARM64 Rust `v4_android_original_m4.rs::tun_worker`唯一真实 `AndroidOwnedTun::read_ip_scatter` 每包在 `original_complete_ipv4_head(head,n,lease)` 原认证/32与L3长度验证**之后**、`seal_android_read_normal_ip`原M1/M3加密唯一PN或旧M3 jumbo拼装**之前**，调用新共享Rust纯解析器 `v4_android_dns_ingress::observe_ipv4_dns53(head,n)`。它只读一份已在原M1 slab的内存，无第二次内核read、fd、IP修改、字节copy、路由/NAT例外或Go/Java逐包通信。

解析按真IPv4总长/头长、非分片 UDP 目标53、UDP长度、单题DNS QNAME/IN/TYPE，禁止原QNAME指针压缩、不完整EDNS和4096以上；TCP仅标“到53的流候选”，不把SYN或碎片化TCP当成已解析DNS。分片、超出首iovec数据和畸形UDP只增加Incomplete元数据计数，**但仍通过原M4原路径透明发送**，因为还没有真正DNS后端和回复所有权；不能用误丢包制造“DNS拦截通过”。新增Rust原Owner只读统计C符号 `wbd_m0_embedded_go_loop_dns_ingress_observed`，三个计数和 `hijack_enabled=0`，以便日后 Android guest P2/P3 以真实TUN业务检验。B2c2a无实际系统DNS监听，也未启Go DNS resolver/Tunnel出站。

新增真实Rust单元测试：原始IPv4 UDP DNS question/TCP SYN等包字节、QR/压缩标签/错误计数/长度/分片/EDNS与单次scatter尾部不完整，原IP包必须字节不变；独立Actions host Job运行`cargo +1.85.1 test --locked -p wbd-engine --lib b2c2_original_rust_m4`，校验原Rust唯一TUN readv、原业务AEAD/PN完整链及只读零劫持开关。ARM64原Go/Rust本体需新Rust符号真实Bionic ELF导出，并维持签名Root APK/同源Linux标准TLS+M4+UDP+Stop oracle。此前B2c1物理NDK socket冷范围已PASS，但尚未Android真实发送。

## 严格分层

本 SOURCE 初始为代码，尚需Actions验收。即使Rust Host5项 PASS也只为 `B2C2A_RUST_SINGLE_TUN_DNS_OBSERVER_HOST_PASS`；**不是DNS截获、普通App Resolver、隧道DNS1.1.1.1实时出口、双上游回复或Android guest P2/P3**。唯一合理后续B2c2b是在原Rust M4唯一TUN owner内完成有界DNS backend +物理NDK socket与Tunnel路径绑定、UDP/TCP53返回原IP五元组/校验和、Stop释放及真实系统Resolver行为；未完前不拦截/不丢弃也不编造成功。ARM64宿主KVM不可访问，P2/P3 ENV_BLOCKED，实体P5最后另授权。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B2c2a接入原Rust M4唯一TUN readv的透明IPv4 DNS53有界识别和只读统计，Host纯Rust逐字节负例/原M1M3保持，尚无实际DNS劫持/Tunnel出口。"}
```

## B2c2a 同源Actions最终证据（2026-11-17）

SOURCE `e22b456155ca30e75d5c86c9c29b903d7ea351c9` [Action #44085089405](https://github.com/lly8666/wbd-next/actions/runs/44085089405) **9/9 Jobs SUCCESS**。独立`b2c2-original-rust-tun-dns-ingress-host`确认5项Rust报文格式边界测试 `test result: ok. 5 passed; 0 failed`，输出`ANDROID_B2C2A_ORIGINAL_RUST_SINGLE_TUN_DNS53_OBSERVER_HOST_PASS_NO_REDIRECT`；source check逐项固定原M4仅一处真实TUN `read_ip_scatter`、原认证`original_complete_ipv4_head`前置、原`seal_android_read_normal_ip`照旧。真实Android ARM64 Rust ELF的新增C符号`wbd_m0_embedded_go_loop_dns_ingress_observed`通过强制dynsym门，B2c1物理socket host4项、B1原Go DNS host7项、B2固定CN8503真源/Host DNS、原M3 LINK20、原Go/Rust Android ARM64 16KiB ELF、独立签名Root APK CN8503 TXT/MIT/source哈希、原Linux服务端真TLS/授权租约/Rust M4双向UDP/Stop oracle均PASS；Linux Job日志`ANDROID_A3_LINUX_SERVER_ORACLE_PASS_ANDROID_RUNTIME_NOT_RUN`。ARM64 Cuttlefish host日志`ANDROID_ARM64_KVM_HOST_ADMISSION_ONLY KVM_NOT_ACCESSIBLE arch aarch64 kvm NOT_AVAILABLE`。

本次只完成**现有Rust唯一TUN入口的不可破坏识别与有界诊断**。其Rust FFI只给UDP候选数/TCP候选数/不完整候选数，`hijack_enabled=0`，**无系统DNS接线、没有DNS backend TCP流重组、没有隧道1.1.1.1独立出站DNS或物理223.5.5.5实际Android发包、没有新的DNS应答回注或改变原M1/M3密文**。Host Rust测试是结构正确的报文字节/边界测试，不是Android真实TUN网络测试；即使9/9不能宣称Android DNS E2E。P2/P3 ENV_BLOCKED/NOT_RUN，实体P5最后另授权，main/M0不改。
