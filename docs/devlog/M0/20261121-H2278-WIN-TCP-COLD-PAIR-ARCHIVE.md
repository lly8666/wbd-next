# H2278 · Windows/Linux 1%/5% 真 TCP OFF→ON 冷阶段工况归档修复（仅测试夹具）

- SOURCE `c5066db61fc51bafd7c2ad2def3029e615efa777` [Action44923149093](https://github.com/lly8666/wbd-next/actions/runs/44923149093)、[44923151036](https://github.com/lly8666/wbd-next/actions/runs/44923151036) attempt1 在真实原 Windows Wintun/Npcap ↔ 原 Linux TUN/Go TLS/Rust 修复OFF阶段完成4核内TCP bulk＋160小TCP回声，核实1% Windows方向1.869Mbps/Linux方向1.737Mbps，P99 938/1014ms；5% Windows方向0.753Mbps/Linux方向0.497Mbps，P99 1890/1522ms。此时唯一可能正确的结论是**OFF实测显著低速，ON比较尚未完成**。
- OFF的第一代 WBD 两端均真实 Stop 后，ON 原生子流程试图 `mkdir(result/wl-public/m029-h2271-windows)`，该目录仍是前一OFF阶段遗留，导致 **`FileExistsError: WinError183`**，两档Action最终 FAIL。问题是测试应用的工况归档，不是WBD网络传输失败。
- 在既有两代顺序 `tools/m0_wl_outer_pair.py` 第一代子流程退出后，只把真实 `m029-h2271-{windows,linux}` 目录移动到本代既有 `outer-pair/off/...`（下一代会进入 `outer-pair/on/...`），从而不覆盖先前数字/原始server、client日志，且让下一代测试入口有干净目录。新 `archive_loss_tcp_stage` 在错误源文件类型、既有目标、不存在leg目录时拒绝改写；不新增产品防御分支。
- 添加真 `tmpdir` 上的 OFF→ON两代实际目录归档单测及CI轻量入口；**此次不触发昂贵 Windows/WSL2 双Actions**（旧主要单机集成易误归因为真实跨机CPU容量）。仍优先H2277的双组三Runner，若取得合格直连原生参考，下一阶段才能把WBD原产品/候选FEC2映射进去。H2278仅单测与归档修复，不代表Windows外层重传ON吞吐有收益，也不更改 Normal默认。

```feature-impact
{"kind":"none","reason":"H2278 repairs only original signed Windows two cold loss-TCP fixture archive lifecycle; Go/Rust product, configuration, ABI and native Stop unchanged."}
```
