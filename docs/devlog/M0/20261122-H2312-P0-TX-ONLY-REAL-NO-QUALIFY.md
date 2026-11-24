# PLAN029/H2312 P0 单变量 TX8→TX16：原 Windows→ARM 双组三机实测（2026-11-22）

**原始 SOURCE** `438f679385ed4e2ace2efe755f7c4ecc9250bf1e`，[Action 45029306636](https://github.com/lly8666/wbd-next/actions/runs/45029306636)：9 jobs **真实 SUCCESS**，两组独立 Win2025 signed Wintun/Npcap+原 GoTLS/Rust → ARM relay → ARM 原 GoTLS/Rust TUN。每组同一 Win VM A→B→A′ 三腿真实接收 + 160 回显/owned Stop；两份 Windows DLL 在此 SHA 真实重编译后核验 ABI/manifest/dll SHA。全程 0% loss，**NPF 全固定 64KiB/16p**；唯一目标变量 TX8→TX16，试验特性不进入默认产品。

|组/腿|A TX8|B TX16|A′ TX8|B vs (A+A′)/2|
|---|---:|---:|---:|---:|
|a 接收 goodput Mbps|332.548|238.151|330.746|**-28.1914%**|
|b 接收 goodput Mbps|169.167|165.749|139.512|**+7.3925%**|
|a Windows CPU s/GiB|15.191|20.1478|17.792|**+22.1708%**|
|b Windows CPU s/GiB|37.8717|34.1355|41.8036|**-14.3135%**|
|a p99 ms|203|172|203|sparse non-regression|
|b p99 ms|266|250|312|sparse non-regression|

NPF 抄收结果全部 `queue_short_calls=0`、`queue_bytes_copied==queue_bytes_submitted`，证明本机驱动复制，不等于对端交付；对端独立 ARM RX bytes 六腿分别 `[1046986752,754434048,1041973248]` 和 `[538247168,525402112,443875328]`。
组 a 每次真实队列调用帧数 A/B/A′ = `7.988 / 9.577 / 7.995`，B 的额外 direct calls `9372` 对 A/A′ `802/696`，其额外零散直接发字节 2,093,590 对 A/A′ 99,465/63,050；组 b 队列帧数 `7.996 / 15.984 / 7.997`，direct calls 288/298/243。**不能据此认定这些零散发送必是源包或根因**，因原 NPF send_packet 同时承担业务单帧、控制、ACK、repair；应在原发送位置分类，再观察 group a 的服务/状态起伏。

**判定**：原生功能双组 PASSED、单变量可操作性 PASSED；稳定 goodput 提速与 CPU/GiB **INCONCLUSIVE/REJECT_DEFAULT_PROMOTION**。双组 A 基线自身 332 vs169，且未证明本次双组 direct 对称 ≥800Mbps 的物理资格，不能把瓶颈归咎于 TX16 本身或宣布600–800达标。该结论与先前 [NPF-only 六腿](20261122-H2312-P0-WINDOWS-NPF-SINGLE-FACTOR-REAL-TRIPLET.md) 相反而互补：NPF-only组a +14.93%、组b−1.16%，也不稳定。

下一步不刷相同场景；通过 opt-in 原 NPF 计数分出 **单帧 direct vs 控制/ACK，实际每次队列帧数分布、active fresh 32/turn、TCP/relay容量**，确认第一瓶颈；随后依项目计划进入单独 P1机会修复，P2最高档 parity 容量门，仍不能提前声称所有弱网业务已达标。
