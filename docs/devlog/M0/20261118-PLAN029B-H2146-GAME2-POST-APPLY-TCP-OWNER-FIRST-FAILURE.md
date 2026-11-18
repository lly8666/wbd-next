# PLAN029B H2146｜真正Game2失败在Go的四lane专属TCP后置门

- 已恢复主分支SOURCE `37f0a19c`，H2144/H2145 [Action44221807203](https://github.com/lly8666/wbd-next/actions/runs/44221807203)/[44221934464](https://github.com/lly8666/wbd-next/actions/runs/44221934464) 只在廉价门FAIL：旧B4/H1934 Python字符串静态测试未承认原始Linux TUN别名现在也供Game matrix使用；不是原生网络失败。准确保留真实B4旧SOURCE PASS，不重跑旧矩阵。
- 先前Game2 [SOURCE347ba373，Action44221640214](https://github.com/lly8666/wbd-next/actions/runs/44221640214) 原生ZIP `14391243445`、SHA256 `cb63bff0eb0f02044022c107b3ebe1a1c19a0891914bcb3ba5889a48faf8ab50`，CRC22 PASS。**真实两条原始TLS、Rust V4 worker、Wintun OS Applied与1313内MTU全部PASS，但在最终Ready之前被拒**：`Game2 DNS/Direct TCP PREPARE: original-Go private Windows Rust owner refused`。Windows本地Stop/Rust Join/WAL成功，完整业务及双端Stop仍NOT_RUN。
- 准确源码首错：`r0/go_overlay/internal/realityfront/bridge_v4_windows_game_native_io.go` 的 `plan029GameTCPControl` 强制 `len(g.members)==4`，尽管该桥`StartNativeGameIOWithColdSplit`和Rust`wbd_m0_win_game_native_v4_tcp_control`已接受原双/四TLS车道。仅改Go后置门为 **len==2或4**；仍原始epoch、LUID、owner、OS Applied状态检查、Defender先于TCP Enable，无放宽非授权组，不改Rust ABI/FEC/repair/wire。
- 更新原assembly manifest该 exact Go source blob，以保证真实编译读取当前版，旧P1/B4静态测试只增加新真实别名branch，不抹去原有保障。新单Game2高级CN [plan029b-game2-cn-real] 原生动作必须观察 physical FakeIP DNS/Direct TCP+UDP、Tunnel双向TCP/UDP、两边owned Stop才能判PASS；其余Game Matrix still NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Enable exact authenticated Game2 two-TLS post-OS-Apply Rust native TCP control by removing previous 4-lane-only Go guard, preserving existing owner epoch/OS and Defender checks; first original failure documented."}
```
