# PLAN028 H1276 — 溢出边界修复与严格三场 ARM64 原生复测

2026-11-06。源事实：H1274 Action [42162179000](https://github.com/lly8666/wbd-next/actions/runs/42162179000) 是原始 SOURCE `d04ace6ce8781f5afea96e3ff76a53ac617b771e`，build SUCCESS，baseline/heterogeneous/pressure 三个 1800s 五客户端 job **全部 FAIL**。H1275 修正了错误的 Game4/成功代际验收口径，但没有修掉实际故障。

## 根因边界：不能合并为一个问题

- H1274 共享 TUN 每租约 `pending_overflow`：baseline Bob=52，pressure Alice=87、Dave=2461，带明确原生 `M0_SHARED_TUN_LEASE_QUEUE_DIAG` 证据。其余场景/客户端计数不证明绝无丢包。
- H1274 客户端 Game2 两条真实 TLS/M4 lane 本地 READY、回收旧组，但服务端同两个 TCP client_port 没有完整 M4 GROUP_LANE_READY：baseline Gen18，heterogeneous Gen6/17，pressure Gen18/30。相应真实 10ms 活跃发送无接收双向业务空洞 83–106s；本次 Rust 队列修复**不等于**修复这个提交协议缺口。
- baseline Bob 无 TC 注入丢包时真实 72.82s 双向业务空洞；pressure Alice 零 TC 注入时约69.8s。二者不是 Game2 故障，也尚无完整可证明根因。
- 异构/高压 Game4 本地真实单 lane READY 4/5，而服务端按客户端源端口匹配 3/3；高损下原始 15s TLS 超时较多，必须区别随机损坏、候选失败、服务端最终 M4 接管。

## 仅修改有证据的窄路径

`crates/wbd-engine/src/v4_embedded_go.rs`：原共享 TUN 每租约 8 包、64KiB、100ms 固定边界保持不变。仅当现有 pending 已满/超字节上限时，**一次非阻塞**重试将排队最旧包送入当前已空出来的原生 M1 inbox；旧包已过 100ms 必须丢弃计 `expired`，没空位仍计 `backpressure/overflow`，owner 已 Stop 则精确丢弃并禁用，不越过 FIFO 或增加其他设备负担。新增原生 Rust 单测模拟“满队列后消费者先释放一个槽位、周期 flush 未触发”，验证第一个 oldest 顺序、第二个按序、无法恢复时仍有界溢出。

`r0/go_overlay/internal/v4productcli/game_linux.go`：保留原始 Go TLS/单端口 443、协议格式、密码/PN/FEC。被拒绝的 TLS cold 候选仅记录脱敏的 `class` 和观察到的 TCP 客户端源端口；认证完成而尚未组合成 M4 完整组的 lane 独立打印受保护 lane_ID 和源端口。下一次 artifact 可确定丢失的是**第二条 TLS 还是组接管阶段**，避免臆测。

## 必须严格复测，不通过即 FAIL

新的 `.github/workflows/m0-plan028-h1276-arm64-30min-remediation.yml` 对新 SOURCE 的原始 Go+Rust **同一 ARM64 build**、三台独立原生 ARM64 runner 并行实际 **1800s** baseline/heterogeneous/pressure，每场五个同时 TLS 认证客户端，IP/TUN/TC/netns/真实 UDP+TCP 与连续 generation，保留 30 个逐分钟方向桶、原始计数、Stop/租约、CPU/RSS、p99、TC 物理丢包、每租约共享 TUN 队列、outer 首发字节 F 和重传已接受字节 R。CI 只有 **全部真换代+服务端真实 M4 匹配**且 `alert_count==0` 时才可以 PASS；否则即使 1800s 业务执行完成仍 FAIL，所有结果无条件上传。

R/(F+R) 按加密 record 字节，**不含控制包 C、IP/TCP/L2、FEC parity**；不伪报全 IP overhead 或 R/(F+R+C)。历史 H998 原同连接在线 MTU 热切换 FAIL、H1259/H1268 Fixed6 S2C 间歇故障持续打开。此文在新 SOURCE 尚未跑完前仅为变更/测试计划，不是产品验收证明。

```feature-impact
{"kind":"updated","ids":["linux-raw-tun"],"reason":"Production Rust original shared TUN bounded per-lease backpressure FIFO correction and same-SOURCE native three-scene verification; Game protected-TLS change only adds cold attribution metadata, no mode/wire policy change."}
```
