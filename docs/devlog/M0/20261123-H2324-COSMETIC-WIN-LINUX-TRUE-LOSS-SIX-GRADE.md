# M0 H2324 · 2026-11-23 同源码 Windows→Linux 表演式外层重传六档实测

## 准确范围
- 产品和夹具 source `92920fb96f2d77ca11abcfdf4a4069d24731f62b`（只含早前已通过原生 Rust/Windows 构建的产品逻辑及后来调整的编排 guard）。自动验收 [#45111930620](https://github.com/lly8666/wbd-next/actions/runs/45111930620) **PASS**。
- 正式架构：Windows 2025 签名 Npcap/Npf、原 Go TLS/Rust DLL/Wintun → 真 Linux WSL2 TUN，Normal、FEC OFF、`outer-repair=on`，每方向 offered 10Mbps、250ms、60s，seed 20261030，legacy 1400 MTU。五档复用基线 #45111958268 的**相同 EXE/DLL、Linux 构件和锁定产品源码**。0% 构件、两端 Stop/WSL 真 Linux kernel 也成功。
- 下表读各独立 Action artifact `report.json`、原 `client.log` 末次 `WBD_WINDOWS_NATIVE_OUTER_REPAIR ... joined=true` 与 `windows-original-go-rust-process-1hz.jsonl`。有损后到包不是业务修复证明；“delivery”指第一次交付，收包减少与真实 netem 相符。

| 双向 tc loss | Action | Windows R/F | 实际 R 字节 | R 包数 | R/(F+R+C) | Linux 首发交付 | Win Go+Rust 整进程 CPU 秒 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0% | 45111958268 | 0.00016% | 134 | 1 | 0.00016% | 100.00% | 8.6094 |
| 1% | 45113200128 | 0.42535% | 367,471 | 429 | 0.4177% | 99.4633% | 8.9531 |
| 5% | 45113205202 | 2.99673% | 2,588,886 | 3,256 | 2.8861% | 97.1376% | 4.8125 |
| 10% | 45113210840 | 7.49695% | 6,476,377 | 8,988 | 6.9266% | 93.6541% | 6.5781 |
| 20% | 45113216542 | 8.93786% | 7,720,406 | 10,330 | 8.1546% | 83.3171% | 6.3750 |
| 30% | 45113223194 | 8.95192% | 7,731,761 | 10,236 | 8.1690% | 73.1027% | 7.7344 |

- F 每档约 86.37–86.40MB；原生重传未知/uncertain 字节均为零；0% 近零；20%–30% ≈9%，所有 R/F <10%；所有六档 `MEASURED_BOTH_OS_KERNEL` + `PASS_BOTH_OWNED`，两个方向真实 netem 有丢包的档位均有 tc drops。
- 30% 明确 `outer-repair-verdict.json: status=PASS_SCOPED_WINDOWS_OUTER_REPAIR`，而 `product_repair_qualified=false`，`repair_signal_grade=NONZERO_WINDOWS_REPAIR_NOT_BILATERAL_GRADE`。**不可当成双端产品资格、P1/P2 完成或重传真可靠性修复**。原 scheme R/F ≈9% 的表演外观已实证，不再人为追强制最小比例。
- Windows CPU 是完整 Go EXE + Rust DLL + Windows kernel 的一个实际进程，包括冷启动和 Stop；不同 runner 的六个绝对 CPU 秒**不等价于**修复前/后、开启/关闭的外层重传增量；不同样本不可直接宣布节省多少 CPU。业务 P99 因双 OS 时钟不同步被明确记录 `NOT_MEASURED_UNCALIBRATED_OS_CLOCKS`。
- 后续高价值唯一微实验：相同 Windows runner、相同 signed Go EXE/Rust DLL 与 Linux 构件，在 30% netem 下串行 OFF→ON，每组 60s，真实双方 ACK 与 Stop，观察进程 CPU 秒、R/F、tc 丢包及相同 SHA；即使两腿 PASS 也只判 **measured CPU difference, not algorithm-attributed optimization**，避免捏造 CPU 增益。
- 本提交属于测试编排/证据账本，不改变产品源码、默认选项、机会式抽样、预算和旧 M2 功能退休结论。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Record genuine source-locked 0/1/5/10/20/30% Windows-to-Linux cosmetic repair ratios and CPU process observations; stage one same-Windows-runner 30% OFF/ON audit; no runtime product changes."}
```
