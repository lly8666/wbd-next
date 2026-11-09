# PLAN028 H1450｜停止同机控制面与被测 VPN 的 Windows L3 刷种子

用户指出第五次同类型 Windows L3 停留在~720s，本次真正的反例是 Windows/Linux UDP RX 6698/6771 仍增长、Runner管理路由 `added=0 repaired=0`，但在已有来源中从不稳定取得原生1800+Stop/清理终值。每20/40s子进程空闲心跳由每60s汇总必然触发，根本无法作为故障探针。过去依次加 /32、重建、换有界PIPE以及日志心跳，都没有跨出同一宿主/控制链故障域，是排障方法缺陷，不应继续相同测试。

核查源码 `.github/workflows/m0-wl-public-normal-full.yml`：`native-public-two-os` 本来就运行在 hosted `windows-2025`，该Windows主机同时承载 GitHub Runner/日志上传和完整VPN Wintun/Npcap/路由/WFP，Linux对端在同宿主WSL2。DNS和0/0恢复不能证明GitHub所有动态出口路由。GitHub本身 [actions/runner#4632](https://github.com/actions/runner/issues/4632) 也报道过2026-08的 Windows hosted Runner失联后 `BlobNotFound` 和45min延迟清理，甚至没有VPN，不代表是本场根因，证明同表象多故障源。

变更：给原 hosted `native-public-two-os` 的 future `[plan028-win-linux-1800]` 加明确的 SKIP 门禁，**不影响在途 SOURCE724a 原job，也不关闭其他已成功短测和ARM64两次1800s**。新隔离架构在 `docs/testing/PLAN028_L3_ISOLATED_CONTROL_PLANE.md`：独立 Linux 控制/取证A、隔离管理面的独立 Windows DUT B、非同Windows宿主的Linux客户端/Server C；独立取证能在B彻底丢失后保留A/C计数、远端存活和真实Stop/恢复。无可用DUT资源时不派发新L3、不标PASS。先短因果对照再一次长测，不换种子。

这次数据面已显示至720s健康，但之后UNKNOWN；PLAN028 IN_PROGRESS，Windows L3 NOT_QUALIFIED，Android/物理NOT_RUN，H998旧FAIL保留。无新产品改动，无029/030工作。

```feature-impact
{"kind":"none","ids":[],"reason":"Scope-only Windows hosted L3 safe gating + isolated control/data fault-domain design; shipping product unchanged."}
```
