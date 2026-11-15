# PLAN029 H1920｜停止H1915无进展票据优化；恢复已验证10GiB版本的公平续传条件

- 新H1917代码SOURCE `fbff58c923dedec097e976820b832114ff673e23` [真实签名Action43712621017](https://github.com/lly8666/wbd-next/actions/runs/43712621017) **FAIL**，非虚假红：Windows原生Go/Rust/Npcap/Wintun和Linux业务Ready、CN FakeIP/Direct UDP/Tunnel UDP、32KiB Direct双FIN/回显及物理4MiB基线PASS（41.15ms）；但4MiB Direct Windows app上传进度打印到786432B后 `sock.sendall` 35s超时，Linux完整4MiB和回显没有发生，完整10GiB **NOT_RUN**。原Go/Rust WAL/finally owned断开限域PASS，不是产品全Stop PASS。
- H1917仅对正字节`recv`后的短读恢复有界续票据，确切signed测试仍失败；原Rust TX最终计数包括`relay_turns20`、`relay_no_progress7`、`relay_progress_no_self_ticket1`、`relay_progress_self_ticket12`、`inner_read_event_suppressed0`、`outer_read_event_suppressed13`，尚不足证明WinSock某一种底层丢通知机制。拒绝再对H1915小优化无证据地反复调门槛。
- 回查H1915提交 `1fabca1` 的真正变更：将H1909/H1913**原真实10GiB成功**的任何`tick.bytes_read>0 || tick.bytes_written>0`自票据，收紧成`buffered>0 || read>=64KiB`。H1920精确恢复**任一真实read或者write进展即一张下一轮公平FIFO票据**，包含写入/排空旧队列而本轮没有读到新字节的情形。无进展后一轮即停止自票据，仍由原WinSock16 shards通知，MAX_QUANTUM8、64KiB每腿、真实WouldBlock与单flow背压、H1916 FD_CLOSE和双FIN保留。无新线程、无10ms定时轮询/每流扫描、不改WFP、MTU或认证。
- 本次代码修改尚未获本SOURCE产品实测；H1909/H1913旧SOURCE通过不能被复制成H1920 PASS。自动真实场景仍然先过32KiB+无pace4MiB双向SHA/FIN/Stop，再跑同VM分段500/700Mbps和10GiB。H1915省CPU假设**暂停**，后继新旧二进制同Windows VM CPU/GiB+小Direct TCP/UDP及Tunnel UDP p99，若无收益不再刷同类测试。
- H1919治理structure FAIL的第二来源是把早期H1915失败证据放入最新H1916 SOURCE的`evidence_refs`。H1920 cursor `last_tested_source` 改成最新确切已测的H1917 SOURCE，`evidence_refs`仅含本H1917失败证据；H1915与H1916历史文件继续原封不动留存。PLAN028限定不重开，PLAN030不启动，029完整出口OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1917 signed native Direct 4MiB upload FAIL and H1920 restores bounded any-progress relay scheduling from prior signed 10GiB successful binary; source NOT_RUN, no product PASS claims."}
```
