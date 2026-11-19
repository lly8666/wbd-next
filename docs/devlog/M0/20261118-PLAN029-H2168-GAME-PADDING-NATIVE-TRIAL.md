# PLAN029 H2168｜Game2/4 startup-padding 最小双机真原生试验

H2167 [commit 2e169ea](https://github.com/lly8666/wbd-next/commit/2e169ead0189f253e465db20444d99202809d3e3) 自动CI真实观察：
- [Action44247188563](https://github.com/lly8666/wbd-next/actions/runs/44247188563) feature目录和governance均SUCCESS；[Action44247188583](https://github.com/lly8666/wbd-next/actions/runs/44247188583) 原assembly、Windows/Linux Rust/Go 编译单测包括原 Rust Game2 off/tls/flows 与 Game4 fixed FEC source两个新test均PASS（Windows Rust 419/419）。
- [Action44247188655](https://github.com/lly8666/wbd-next/actions/runs/44247188655) r0 native ABI SUCCESS，[Action44247188585](https://github.com/lly8666/wbd-next/actions/runs/44247188585) native functional 编译/5分组SUCCESS。
- [Action44247188485](https://github.com/lly8666/wbd-next/actions/runs/44247188485) 另一个旧M4 Windows Rust owner历史冻结夹具编译FAIL：原legacy realityfront三个测试结构体引用不存在的 ClientConfig.RootCAs 字段；非Game Padding当前真实NPF故障，不修旧来源扩大本次改动。

本批只接一个source-lock [plan029-game-padding-real]原生Action，正好 **Game2 FEC off** 与 **Game4 FEC fixed** 两个独立Windows2025/WSL2真实driver作业，每个同VM同SOURCE顺序 cold off→tls→flows 三代。仍走原Go TLS、原Rust Game Adapter/AEAD、Wintun/NPF、原WSL2 Linux TUN、真实内核UDP及Windows→Linux TCP echo（tls arm仅附TLS-record样式头，不宣称应用TLS协议握手）、双方Stop/WAL。只验真实OS Applied、原模式effective、每代Rust FEC模式、真实 M4 NPF successful-copy receipt (off=0, tls/flows>0)、物理MTU1460、同源Go/Linux二进制SHA，不重复5政策×4组合20例，不跑030。

试验wrapper `tools/m0_plan029b_game_padding_native.py` 首错FAIL并保留所有日志/真实SOURCE，独立写JSON，不冒签名实测。原H2162 PASS保留，不把编译/设计当正向物理结论。待Action严格观测后才能更新feature card verification、M0 last_tested_source/evidence_refs。全技术PLAN029/029B仍OPEN，Linux主动Windows入站TCP另计NOT_RUN。

```feature-impact
{"kind":"none","ids":[],"reason":"Only add source-locked minimal Game startup-padding native test driver, constrained workflow and optional real TCP TLS-record-prefix probe; product Game/GUI code and feature cards unchanged from H2167."}
```
