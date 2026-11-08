# PLAN028 H1422 | 只修本轮源码装配哈希和真正执行的 Go 正反例

2026-11-09。H1421 SOURCE `e2a74d8090fc324524fed66587ec158c6af70fbc` 把 Windows+Legacy 共用 server 的 original SYN persona 配置由进程级改为每个已认证 TLS/Rust M4 原生 owner；**新网络业务没有执行**，不是修复已 PASS。自动触发原 Action [42501747637](https://github.com/lly8666/wbd-next/actions/runs/42501747637) 首错为 `tests.test_m0_install_public_faketcp` 两项失败，关联 [42501747629](https://github.com/lly8666/wbd-next/actions/runs/42501747629) 与 [42501747649](https://github.com/lly8666/wbd-next/actions/runs/42501747649) 都是 `FEC2_ASSEMBLY_REJECTED: overlay result blob mismatch: internal/faketcp/packet.go`，提前退出，网络 NOT_RUN；老失败原样保留。

真实源 blob SHA 分别为 `packet.go=54a2985692ebad78cd8c9f48bfa6a941c7f72215` 与 `association.go=da57240c038393b8b2be3a5b6af977a4d79c8a5c`，旧 `manifest-plan020-m0.json` 尚写历史哈希。H1422 精确同步**两个** manifest 的对应 result_blob，原 donor pinned original_blob 不变；绝不关 manifest 的强校验。另新加的 H1421 persona 正反例原本只是仓库文件，不在 donor assembly，`go test ./internal/faketcp` 其实没执行。本次以独立 `create` row 正式装入，保持旧7个 FakeTCP核心文件计数不变。反例原先意外擦掉 MSS option type，导致未触发有效负例；修改 TCP SYN 最后一个 pad NOP 为 EOL，保留 MSS/SACK/WS 的真值，只让布局不再 canonical。随后以标准 source-locked build+单一 Windows＋Linux 双端业务核实际 persona/UDP/TCP/Stop，不补判 H1420 Linux B FAIL，不调 TLS/Rust/checksum/FEC 或加防御框架。

```feature-impact
{"kind":"none","ids":[],"reason":"Source-lock exact Go assembly result blobs and ensure existing cold SYN persona positive/negative tests actually compile/run; no product hot path or protocol change."}
```
