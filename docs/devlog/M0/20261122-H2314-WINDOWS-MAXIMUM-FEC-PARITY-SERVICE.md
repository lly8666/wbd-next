# PLAN029/H2314 · 固定最高档 FEC 真正服务量：Windows 原生发送施工（2026-11-22）

## 源锁与边界

- 施工源（原实验，不在 main）：`3d2d670826520c5c25a12d5551d8ec49080c1f61`，[原生 Windows Action 45030957556](https://github.com/lly8666/wbd-next/actions/runs/45030957556)，**static + windows_unit 两个 Job SUCCESS**；之后的注释/验证和实验夹具变更不能冒充该 source 自身运行。原始 [PR #68](https://github.com/lly8666/wbd-next/pull/68) 仍 Draft；产品 default OFF，不合并本优化。
- 原 Windows `v4_windows_native_runtime.rs` 每次原 TX work turn 处理 `RX_WAKE_BATCH=32`、源包 `BATCH=8/16`，但**仅一次** `send_fixed_parity`，其中 `stage_fixed_parity_entry` 一次最多4条。对持续闭合的 k16/r20 Maximum 固定 FEC，理论原服务量 `4/32=12.5%`，而完整数据需 `20/16=125%`，约有十倍服务预算缺口。这是**控制流上界**，不是已经从产品实测抽出的实际发出率；低源速率/定时 tick/部分 block 会不同。
- H2314 引入专门编译实验特性 `h2314_windows_fixed_max_burst`，仅原 Rust owner、`FixedStream` 和原 M3/AEAD/NPF：一个关闭的 Maximum `k16/r20` FEC job 按 M1 已接受的 `poll_parity_quanta(max_quanta=5)` 组20条 frozen FEC parity，M3 original AEAD 仍逐 row 真实分配 seq/PN，透过同一 Win NPF sender 的 `send_batch`（在16-frame NPF64 下以16+4两个真实 queue syscalls发送）接收 driver copied prefix，**只在同步 copied/not_sent/uncertain settle 后记账**。每个32-ready源 turn 最多服务两个原始 M1 job，即预算40/32=125%；包含 stop fence、非Auto最高档检查，无第二工人、无重传同包、无跨租约 HOL。
- `WindowsFixedParityBatch` 对外原 C ABI **保留4条**，仅内部新增20条容器；默认、Auto 和其余 Fixed 档仍用原一次4条 quanta 路径。0-copy / frozen source-first 后再 parity，无新的 Go 密钥操作。
- 本轮原 Windows Source-built tests：`m0_windows_fixed_maximum_twenty_frozen_rows_one_original_prefix`（16个源/20个 parity，PN/seq 连续，staged前 `r_sent==0`，错前缀无法 settle，同一个 job 不重复封包），原已有 `m0_fixed_stream_full_maximum_five_quanta_one_genuine_m4_prefix`，`native_driver_prefix_never_claims_peer_receipt`；全部 native unit SUCCESS。真实双 OS 原 Go TLS signed NPF→ARM FEC Maximum 0%/1%/5%、`copied_parity_per_source_ppm`、端到端修复成功数和400Mbps**尚未进行**；不能将 unit=product。
- 同一个原生 owner Stop 在这个特性下输出 `PLAN029_H2314_MAXIMUM_PARITY_STOP`：copied_source_rows、copied_parity_rows、staged_wide_batches、copied_parity_per_source_ppm，与理想1250000ppm对照；报告明确 driver copy ≠ remote parity/receipt。以真实 receiver M3 repaired block/inner TCP bytes、上/下行CPU/GiB、Stop 和 direct physical >=800Mbps 另行资格判定。

```feature-impact
{"kind":"none","ids":[],"reason":"仅新增默认关闭的 Windows 原生编译实验特性 H2314/H2313 以及源锁单元/Stop 观测；未发布新产品功能 ID，未修改公开 Go FEC/Auto API、正式配置、默认档或用户可用行为。真实 maximum FEC 网络性能仍 NOT_RUN，不声称晋级。"}
```
