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
