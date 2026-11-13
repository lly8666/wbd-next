# PLAN029 H1701｜修新 Rust 编译首错与功能卡预算，不重跑旧场景

- [H1700 source 52efb211](https://github.com/lly8666/wbd-next/commit/52efb21170cd3ed59019d07c38c3a5b40a270e80) 的 Windows/Linux Rust eligible library test在加入物理UDP和fragment测试后均 **FAIL 编译**。首条明确Rust `E0425` 为新增test中局部 `let dest` 而 FragmentKey写 `dst` 未命名；修成 `dst:dest`。平台UDP `Result<DirectUdpPayload,DirectUdpError>` 测试三个assert_eq需要 `DirectUdpPayload` 的 `Eq,PartialEq` 派生；加上纯派生、不调整网络语义。旧H1699跨平台11 test PASS保留，不能继承给未通过的H1700。
- 同SOURCE [Governance 43347750979](https://github.com/lly8666/wbd-next/actions/runs/43347750979) **SUCCESS**，上轮 H1699 证据SOURCE不匹配已修；Feature catalog **FAIL** 仅因为 windows-native-transport JSON超出16KiB严格预算。保留29条历史 verification 全部status/source_sha/evidence，不删除任一原始结果；将冗长platform/scope展示压缩成短摘要，历史完整度通过直接引用现有不可修改原证据。此卡格式使用单层缩进，写入前计算UTF-8总字节小于16KiB。
- 本次仍是编译修复和验证计划，尚无物理Direct UDP出入口和有界IO worker。保留 H1694 signed Wintun Defender Allow A/B/C genuine TCP capability + H1697 4-stage no-WFP Win32 Apply/Stop scoped PASS。其余 DNS53/FakeIP TTL、GUI/startup padding与 D1–D5/P1–P2 仍未完成。

```feature-impact
{"kind":"updated","ids":["windows-native-transport","dns-split-ipv6"],"reason":"Fix H1700 exact Rust platform/fragment fixture compile errors and keep historical feature-card entries under 16KiB without dropping any source/evidence/status."}
```
