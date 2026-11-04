# PLAN028 H1087：route-key 限定收口，继续 Game 交接

按最新 main/cursor 已收在途 Actions。仅将 **32B route-key 本地预置/导入、缺失本地拒绝、WB-R1/37B 双向私有前导移除、证书验证与 TLS 密码保护** 这一工作范围限定收口。真实 SOURCE `7b38d2baddaa41ab5e410d2533a1e8c396510745` 的 [Windows Npcap↔WSL2 Action41761356866](https://github.com/lly8666/wbd-next/actions/runs/41761356866) 及工件13290631778 已独立复核：TCP重组首 CH667B/SH127B、SessionID32B、无私有前导和服务端抢先数据，真实UDP/TCP及双端Stop PASS；Linux x86 与 native ARM64 Game 4+4 CH/SH 限定证据分别保留。

**完整 TLS 契约尚未全部收口**：TLS1.3 Certificate/CertificateVerify/Finished 独立转录和同配置 Go/uTLS 基线比较仍 NOT_RUN；外站指纹不能据首包推断。Windows 真物理 NIC/IP、Game健康 A→A+B→B、H998 真实在线 MTU 收窄 FAIL、旧 ARM64 Game4FEC FAIL、CPU/p99/远端 ICMP、Android 全按历史限定保留。无需重复派发已PASS的原生首飞测试。

后续优先复用现有 Rust SharedTun 单TUN reader + /32/默认路由的按 generation 精确切换，补 Linux Game 客户端真正 overlap，不重写任何 FEC/record/AEAD/PN；本 Linux 任务按用户要求双端 x86，下一新任务双端 native ARM。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1087 route-key/offline provisioning + removal of private WB-R1 first payload scoped closed by source7b38 Win/WSL2 original Go/Rust real TCP and business. Full TLS transcript/reference baseline and all PLAN028 lane handover remain open."}
```
