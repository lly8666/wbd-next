# PLAN029 H1946｜中断恢复与 P1 CN 冷源首故障

- `main` checkpoint `6848c0d` 之后仅有 H1945 SOURCE `72d3e131561dcb54501722f7d9254b34a27094e9`。取回 [Action43771212764](https://github.com/lly8666/wbd-next/actions/runs/43771212764) 实际 Windows/WSL2 原生成功，而不是标题 `no-scene` 所暗示的未测试。QPC 同 VM 384/384 对齐；FIN-first / payload-first Rust 首次 inner WinSock write→应用 recv p99 = **0.476 / 0.450ms**；应用 FIN→Rust write p99 = **17.317 / 15.845ms**。4MiB、两种 TCP 回包顺序、Tunnel UDP、owned Stop PASS；来源不同端时钟不混用，**p99 根因与 CPU 仍 OPEN**。
- 取回 [H1937 Action43734219846](https://github.com/lly8666/wbd-next/actions/runs/43734219846) 原始 `plan029-p1-ab/A1_all`、`B1_cn` 工件。A1 真实 0.69839GiB、双向应用/Stop PASS，Windows Go+Rust 进程 21.6792 CPU s/GiB（不是 Rust-only）。B1 真应用/Stop PASS，冷行 `route_mode=bypass-lan-cn cn_rows=8 domain_bytes=180224`；首个 P1 失败是 **CN 未加载 4096 条测试 /32**，不是 H1936 的 Windows TCP ACL。B2、A2、P1 同 Rust CPU 四臂比较均 **NOT_RUN**。
- 定向旧 Go/Rust 复习：`m0Plan029ColdSource` 的 `cn=o.Bypass4` 读取 OS 紧凑 bypass 字段，而实际 B1 只有八条 LAN 合并前缀。H1946 增加 `m0NativeV4Options.ChinaIPFile`，从原 `--china-ip-file` 单次读取 canonical Rust CN 快照（内含 LAN 并集，仍无海量 OS routes）；无效/缺失显式文件 fail closed。锁定 Go 4096 非相邻 /32、小的陈旧 LAN-only bypass 和坏文件测试；manifest blob 同源更新。
- 新 SOURCE 的 **单 Action** 仅以 `[plan029-v3-real-p1-tunnel-ab]` + `[plan029-v3-real-p1-policy-abba]` 顺序进行 A1→B1→B2→A2；提交时全部 **NOT_RUN**，不得从新源码静态门槛直接晋升 P1 PASS。没有重发 H1945/P2/10GiB；沿原 WAL/owned finally 恢复。更多 D1–D5/P1–P2、Game4、GUI、IPv6 和全量性能仍 OPEN。
- 证据：`docs/evidence/M0/PLAN029-H1946-H1945-QPC-AND-H1937-P1-FIRST-BOUNDARY-20261116.json`；H1937 历史失败留存，未触 PLAN028/030。

```feature-impact
{"kind":"updated","reason":"H1945 true QPC receipt and H1937 first P1 CN cold boundary; H1946 one-source Go Rust cold-fix not yet native-qualified","ids":["dns-split-ipv6"]}
```
