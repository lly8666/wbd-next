# PLAN029 H1695｜收真实签名 Windows A/B/C PASS，并消除 Rust shared FlowPin 满表误挡 Tunnel

- [Action 43338614004](https://github.com/lly8666/wbd-next/actions/runs/43338614004) **SUCCESS**，原始 SOURCE `9b4d5adafb661bd405a9fe53254daf9754043030`、签名 Wintun 0.14.1、真实 Win32 IP Helper + /32、kernel ring/原生 TCP+UDP listener。真实 artifact [13997853069](https://github.com/lly8666/wbd-next/actions/runs/43338614004/artifacts/13997853069) zip sha256 `f30fc51afaaaf43ad586fa0bca3a4fa86fa01671223e810469093db68c85153c`。
- A：无本程序 Defender 规则，UDP listener 2.5s 未到，TCP SYNACK 6s 未到。B：程序+TCP/UDP+local/remote IP+精确端口的2条临时 owned Defender Allow 真实 readback；UDP listener 收到，TCP SYNACK 收到，继续真实 `Accept→DATA→reverse DATA→FIN/EOF` PASS。C：精确名称删除2条并读回 `VERIFIED_ABSENT`；随后 UDP、TCP 重新不达。**这是有因果的内核接入能力正例**，但不意味着无其他环境限制、全机DNS、物理Direct出口或产品Ready。
- 后端定案：**只选 Windows 本机内核 TCP 接入＋ Rust 异步物理socket两腿**；不并养 smoltcp 或旧Go gVisor稳态包泵。对产品需要的本机listener允许项另做少量 exact-owned cold lifecycle；不得恢复旧项目自定义 WFP guard。H1669/H1672/H1690 的无Allow真实失败不改写。
- 追加 Rust `v4_client_split.rs` 的 `FlowPin` 独立 direct_hard 与 tunnel_pin_soft：前者满只拒新 Direct，Tunnel 缓存满继续交旧 owner 的 Tunnel，不共享拒流入口；RejectUnknownFakeIP 直接返回拒绝并不占map，保留已有 pin 出口固定、FIN/Stop 后释放。已加上 full/oldflow/unknown-fake/局部回收纯单测。**本条代码提交时 CI 未跑，不宣称真实 ingress 或资源压力 PASS**。
- 历史 [M0-WIN-LINUX 43248553062](https://github.com/lly8666/wbd-next/actions/runs/43248553062) public two-OS **FAIL**（Windows client Ready 前旧 `crash-persistent native DNS and IPv6 guard required`），不可归咎未实现的 029 direct；今后按新 §3B 放开真正可执行 no-WFP OS 测试入口，Applied 只能按当次实际 stage + Rust native owner 自检。
- Remaining: 将此 native TCP 资格接入 Rust ingress、物理Bound TCP+UDP出口、owned return NAT/Stop；DNS53单入口/选择性FakeIP与真实配置、no-WFP四阶段OS/防火墙owned生命周期、startup-padding、D1-D5/P1-P2。028限定H1657不重跑，030不开工。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Collect real signed A/B/C Windows native kernel TCP/UDP ingress PASS with exact owned Defender restoration and repair direct-only FlowPin hard-cap semantics without blocking Tunnel cache."}
```
