# PLAN029 H1803｜D3 CN 多 A 写盘前容量失败的安全回收

- 基线 `e63a12db67f445381b5ca44110a205e82ad2014e` 已过 [governance Action 43562462488](https://github.com/lly8666/wbd-next/actions/runs/43562462488)。审查发现 UDP/53 与 TCP/53 两处顺序 CN A `FakeAllocator::prepare`；若多 A 的后继项达到 FakeIP entry/byte hard cap，则先前本次新增但未写盘/未发布的槽滞留占用容量。
- Rust `prepare_batch` 将整条 DNS 答复的候选先于同一次 journal 持久化完成。**只在 journal 尚未开始而批量准备失败时**，撤回本批新预留未公布的槽，修正 key/expiry/字节账，允许更小后继答复恢复。先前已有、被引用、已公布，以及此前可能已写盘但回执不确定的保留槽绝不能清除；`persist_batch` 失败也不做回收。
- Windows Native original app UDP53/TCP53 共享该方法，无 Go 热泵、无额外解析器/OS 资源。新增两项真实小配额纯 Rust 单测：老 active held + 新 multi-A hard full；老 journal uncertain + 新 multi-A hard full；检查局部拒绝后正常单 A 恢复。当前只记 **IMPLEMENTED_NOT_TESTED**，本 SOURCE Actions 返回后再判断 BUILD_PASS/FAIL。
- 真签名 Wintun D3 容量/多A恢复、D4 IPv6/partial Apply、D5 GUI effective/1万规则、P1/P2 CPU/GiB+p99/queue age 仍为 NOT_RUN；不重跑 H1799、不恢复 028 矩阵。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"A failed CN multi-A reservation now releases only fresh unpublished slots before any journal work; original native UDP/TCP53 share one bounded FakeIP batch method."}
```
