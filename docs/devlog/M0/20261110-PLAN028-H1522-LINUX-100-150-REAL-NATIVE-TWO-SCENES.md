# PLAN028 H1522｜Linux 双端 100–150 Mbps 外层真实压测开跑（0% / 30%，独立 Runner）

- 用户请求在接续 Windows 前序验真的同时，跑 Linux 客户端↔Linux 服务端相同五模式客户端、双向大小包 UDP/TCP，并把**实际外层总带宽（两方向合计）**提高到 100–150 Mbps。现行 x86 六个真实 netns 原 Go FakeTCP TLS443 + Rust ISA-L TUN、五个独立账户/地址原夹具复用；没有改 FEC/Game/record，不生成新稳态探针。
- Frozen PRODUCT SOURCE `9b2605538d9e05af5b0c2a93bc7a7bc8495ed8da` 的 Linux 原生 release Go/Rust/ISA-L 两端已在 Action42775103187 完整编译并上传 artifact13744140576（同源 manifest/SHA256，非跨版本混拼）。本轮 wrapper `4a8bc5faa47769b58d08cf1b3ae3880a6c126810` 只改压力夹具/离线报表，原 `capacity75` 未修改口径。
- 选择五客户端每方向内层业务基本负载 12+8+6+3+6=**35 Mbps**、双向70 Mbps；256/1024 混包，近似 5512 logical PPS/方向（按加权均包793.6B，实际 PPS 由真实测试读回），尚未计真实 Game 多lane、副本、FEC 有效符号、IPv4/TCP头。200ms/方向≈400ms传播 RTT，在途逻辑量按35Mbps×0.4s≈1.75MB/方向，按宿主核心和 netem 真队列实测判断是否需要缩小；目标内层不是外层测量。
- 两端五条物理 veth 均装真实 `tc netem delay 200ms loss 0%` 或 `30%`，独立 Action、独立 VM；四阶段 90s 0.6× →180s 1.0×→90s 1.1×→230s 1.0×，另 10s warmup。只读 `tc -s -j` 对十个 netem 的 10 秒`Sent bytes/drops` 分方向求和；验收以 sustained/recovery 真实外层 100–150 Mbps（有70%以上有效窗且稳定均值在范围）+双向真收件为准，不拿网卡/配置 target 假装测量。H1504 宿主每核、MemAvailable 30 秒容量停止器在旁，容量限制明确标出，不降低数据完整性/Stop/秒级断流门槛。
- 第一轮 Actions [42781392677](https://github.com/lly8666/wbd-next/actions/runs/42781392677) / [42781392774](https://github.com/lly8666/wbd-next/actions/runs/42781392774) 离线套件 PASS、manifest 预检因本轮新 YAML Python ELF 字面量转义重复导致最早 Assert FAIL，**原生网络 NOT_RUN**。立即一行改成`bytes.fromhex("7f454c46")`，未改产品；新 Actions [42781585712](https://github.com/lly8666/wbd-next/actions/runs/42781585712) loss0、[42781585834](https://github.com/lly8666/wbd-next/actions/runs/42781585834) loss30 已通过前置且执行原生网络步骤。不能在结束前宣布 100–150 达标。
- Windows 前一 Action [42775103187](https://github.com/lly8666/wbd-next/actions/runs/42775103187) 真原生 loss0 job129693456709 原始 FAIL，原 ZIP artifact13743658475；日志转发线程`UnicodeEncodeError(cp1252)`属诊断层异常而非直接产品首因，线程退出让原产品首错日志未在 job stdout 显示。不得把 Windows业务定为 PASS，亦不以单个转发错误宣布产品 FAIL 根因。需要原始 ZIP 或只修诊断后定向再现。
- **未覆盖**：Linux 场景使用现行 timer/真 TLS 新代与 Game 单lane 热轮换，非 Windows 真实物理源 IPv4 改变；物理 WAN/Android 不在这两场。028 仍 **IN_PROGRESS**。

```feature-impact
{"kind":"none","reason":"This only creates source-locked native Linux five-client outer-bandwidth tests, kernel telemetry, offline verdicts and evidence; no product feature/protocol code changed.","ids":[]}
```
