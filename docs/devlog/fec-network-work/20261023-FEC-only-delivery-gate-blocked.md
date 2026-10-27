# FEC 网络独立任务 — 合并门槛报告（阻塞，不可合并）
日期：2026-10-23。工作分支：`experiment/fec-network-tuning`。冻结 native 源码：`7ad7e0e11bd6fa130cb10c147c52ed33a5ec9c57`。

## 实施与证据
- 原生 Linux V4 authenticated owner 的 `--outer-repair=off` 在启动 worker 前应用并读回：不登记 outer frozen DATA shadow、没有 repair candidate/raw resend；保留独立 M2 首发质量观察、reverse authenticated receipt 和 FEC parity。默认 ON 仍保持既有算法，不重写外层恢复调度。公开 Game OFF 显式拒绝。
- Python fixture 实际传递两端开关，校验双方真实数值读回以及 OFF 时 `original_frozen_retransmitted=0`、candidate/shadow 为零。缺读回一律失败，不能用 NOT_OBSERVED 伪装 0。
- 固定最高档源码 unit 在 ARM64 [Action 39915080946](https://github.com/lly8666/wbd-next/actions/runs/39915080946) PASS；原始 Go+Rust ARM64 公共产品[构建 39915080968](https://github.com/lly8666/wbd-next/actions/runs/39915080968) PASS。工件 12484770973，GitHub SHA256 `fd22c47a4f57fe5968f4ffb927ba7e284217c0a3fd2b3a3271ab583b600d98f4`，没有重新编译测试工件。
- 夹具合同 [39915081006](https://github.com/lly8666/wbd-next/actions/runs/39915081006)、[39915604278](https://github.com/lly8666/wbd-next/actions/runs/39915604278)、[39915779231](https://github.com/lly8666/wbd-next/actions/runs/39915779231)、[39916080150](https://github.com/lly8666/wbd-next/actions/runs/39916080150) PASS。
- 固定档带 loss0→5% 的独立场景 W1 [39915604295](https://github.com/lly8666/wbd-next/actions/runs/39915604295) 在 shallow checkout 的请求路径预检失败，已经按 HEAD 父提交 fetch 修复。W1R [39915779256](https://github.com/lly8666/wbd-next/actions/runs/39915779256) 下载 Artifact ZIP 跳转得到 HTTP 503 `Egress is over the account limit`；W1RR [39916080164](https://github.com/lly8666/wbd-next/actions/runs/39916080164) 以 Actions 原生下载，确认 artifact ID 后 Blob 连续五次下载失败。**三个场景都尚未启动产品**，不是 FEC 失败或通过。
- 已支持在同一个性能 job 按预先锁定 AB/BA 顺序跑旧 A 和新 B：A 不指定 `repair_enabled` 不会传旧二进制不认的 CLI 参数；B 可声明 `repair_enabled=false`。独立 case 可通过各自 commit/source 键并行，但资源门未满足前不安排重测。
- 理论 IID30% maximum MDS `r=ceil(1.25k)` 的单源残余：k16 0.02282576%、k8 0.38078174%、k4 1.7390295%、k1 2.7%。这是模型，不是实际 decoder 或首次交付。

## 未满足的交付门
真实相同两侧参数生效、实际 outer 零 DATA 副本、原生 FEC parity send/receive/recovered TUN、auto 真实反馈与升降档、端到端 loss0/5/20/30、实际 CPU/RSS/p99、容量、STOP、旧新同 VM 对照均 **NOT_OBSERVED**。不得合并或写 PASS。旧网络岗位的协议计数缺口和 `next_action` 未接管。

## 容量停止与解除条件
工件下载外流能力不可用，已停止新增性能 Action；不得增加业务 Mbps、重复推送场景或重编译同源试图刷绿。恢复 GitHub/Azure Artifact 下载以后只重跑现有唯一 W1RR 的预置工件，先验双端 OFF→反馈→实际 FEC 恢复→首次交付→CPU/RSS；已验证的构建/单测复用。再独立评估 Auto 与匹配 old/new AB，不跨 worker 合并宣称。
