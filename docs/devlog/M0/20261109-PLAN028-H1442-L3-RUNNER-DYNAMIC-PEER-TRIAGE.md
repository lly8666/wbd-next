# PLAN028 H1442｜原生 Win/Linux 960s 中断的管理路径差分

三次长测并非在同一秒触发了产品故障。Windows 原生 Action42508261361 和 42517812264 的 job 各经过约 62–63 分钟转 FAILURE，原生 stage19 的原始步骤却无 `completed_at`、最终原日志 `404 BlobNotFound`；本次 Action42532903160 源 `24537be41befd4a3554a6cdd780716d04dc16670` 的用户原生标准输出明确完成认证/管理路由安装，双客户端真实交付连续达到 **960.2s：Windows UDP RX=8925、Linux UDP RX=8971**，但截至核查 native stage19 无最终 1800s/Stop 回执。唯一确定结论是宿主/Runner回报链与产品业务证据需要分开；真正的停止点及新连接变化尚未证明。保留原 Action 及证据 `docs/evidence/M0/PLAN028-H1442-CROSSOS-960S-RUNNER-MGMT-GAP-20261109.json`，不重写旧 FAIL。

**可区分假说的最小改动：**当前 `m0_wl_gamefec_management_route.ps1` 在正式业务启动前仅固定四个已建立的 Runner TCP 对端 /32。长测中若 Worker/Listener 重连到新 IP，原绑定无保护。新增仅对显式跨OS 1800s `Refresh`：10s 左右经原 PowerShell OS API 只查询实际 Runner.Worker/Listener PID 的 `Established/SynSent` IPv4，若出现新目标，按已有精确租约 owner+SOURCE+原物理 NIC/下一跳 CAS 持久化和读回，绝不路由产品流量，最后沿原 Restore 释放。原 GameFEC/Normal105 `Arm/Restore` 不变；24 路由有界，仅属测试宿主管理，非新产品控制器。原生 long helper 报本次刷新次数/新增路由数（新增为0则机制未触发，不宣称根因修复），真实 UDP/TCP/1500ms/1800s/Stop 全部保留。旧纯长度回归预算由85行更新为135行，语义 guard 仍由精确字符串及新增 L3 作用域校验约束。

**决策：**一次新的差分 Action，优先看 `H1430_REAL_RUNNER_MANAGEMENT` 中确有新增连接并 OS读回，以及末端的真实 app+Stop。若无新增目标而仍掉日志，改为采集宿主独立时间轴，停止无依据调参数/刷种子。PLAN028 保持 IN_PROGRESS，已有 ARM64 两独立 1800s PASS_SCOPED 不重测，Android/物理未跑、H998 老同socket 热缩FAIL保留。

```feature-impact
{"kind":"none","ids":[],"reason":"Native PLAN028 Windows-Linux L3 harness only: run-scoped management /32 refresh and diagnostic readback; no product/data-plane/MTU/TLS changes."}
```
