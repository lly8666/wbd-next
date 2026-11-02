# PLAN027A H931｜Windows Wintun 单包超限不再 Stop

当前原始 Windows M4 ring `n4ReceiveReadyIPv4` 在获得真实 Wintun ring loan 后，若合法 IPv4 尺寸超过 owner 的 bounded scratch，会 **Release** 当前 packet、保留该 session，但返回 `io.ErrShortBuffer`。Windows Game peer `transmit()` 将该错误直接上抛为整个 owner 停止。Normal/FEC 原单包错误计数通路也无法精确区分超限与坏包。

本批不重构驱动或造 LINK。固定内核 ring 成功释放后的精确 sentinel `ErrN4NativeFrameOversize`，只经现有两套 peer 的`ReceiveReadyIPv4`消费者转为本包 `oversize/mtuDrops`、continue；未知 Wintun/OS 不确定结果仍沿已有 Stop 和 WAL。完全不把 truncated bytes 传给 Rust Game/FEC，不申请重用旧repair PN或再次 seal。真实 DF0 应先由 Windows IP栈在 Wintun 前分片；对超限仍进入 ring 的额外异常此批**只丢本 datagram**，不承诺大包完整送达。source-locked PLAN020 manifest 的3个改动文件 Git blob 和本次变更同批更新。

H927 Windows original WAL SOURCE `e854377f` Action `41435387868` **PASS**（仅编译/原WAL现有用例），原 H926 `41434561392` 因旧测试调用删除Go预算公式 FAIL 的事实保留。H930 Rust Linux Game DF1 仍待同 SOURCE native OS 验证。新 Windows 所有模式+大包/DF测试 **NOT_RUN**。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Windows original Wintun ring oversize is a released one-packet nonfatal sentinel; Normal/FEC/Game handle it without Stop; pin modified original Go source blobs in PLAN020 manifest. No fake LINK/fragmentation claim."}
```
