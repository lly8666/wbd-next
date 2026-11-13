# PLAN029 H1743｜只跑一次真签名原Go TLS＋Rust V3纯Tunnel、OS Stop场景

- H1742 SOURCE `1709ea92b1662909bc1b55b43a14cb2cc7735c2e` [Rust Windows/Linux 43412698406](https://github.com/lly8666/wbd-next/actions/runs/43412698406)、[跨ABI43412698604](https://github.com/lly8666/wbd-next/actions/runs/43412698604)、[治理43412698439](https://github.com/lly8666/wbd-next/actions/runs/43412698439) 全部PASS_SCOPED；仍不是029实网产品证据。
- 首次真正原Go V3接线只选一次`[plan029-v3-real-tunnel]`：GitHub Actions源码锁定编译原Go EXE和Rust release DLL，追加私有`m0_v4_probe` feature（普通release不编入），同一凭据TLS+单Wintun Rust TX/RX，使用已有正式Win2025/WSL2 Linux原生APP双向UDP/TCP+Stop夹具。
- 本场`--route-mode all`，否则Ubuntu 10.66.0.1在LAN例外直接物理连接，不能证明Tunnel。证明`WBD_PLAN029_V3_TRIAL_COLD_EFFECTIVE route_mode=all`、原OS Applied、原Rust原凭据应用真实双向交付、确切`M0_PLAN027_NATIVE_STOP_RESULT`、最后v2 WAL和routes sidecar均不存在才单独写`PLAN029_H1743_..._PASS`。
- **严格限定：这是唯一纯Tunnel接线能力门，非D1/D2分流双出口完成；DNS双purpose、Direct TCP/UDP、Defender/旧WFP独立结果仍NOT_RUN**。不恢复028的七模式或老WFP，真实第一FAIL保持原source和日志，优先修而非重复探针。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Source-lock one genuine signed Windows original-Go TLS + Rust V3 Tunnel-only first/reverse UDP/TCP and owned four-stage Stop scenario; keep all untested Direct/DNS outcomes unqualified"}
```
