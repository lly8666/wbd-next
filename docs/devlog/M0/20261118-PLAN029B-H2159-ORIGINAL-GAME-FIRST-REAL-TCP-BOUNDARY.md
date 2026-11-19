# H2159｜原Game2/4四独立签名任务首个真错：历史反向入站TCP门混入Game分流

[Action44232480332](https://github.com/lly8666/wbd-next/actions/runs/44232480332) 原SOURCE `1a662439ade52233974e1a69c9db4f8c18300e6e` 的四个Windows2025/WSL2 Game2off/fixed Game4off/fixed job **全FAIL**，分别均止于首个off，后续all/LAN/ordinary/advanced **NOT_RUN**。廉价/WinGo/WinRust/LinuxRust、原Linux Go+Rust构建PASS。下载3份真原始ZIP（game2off SHA256 `aebc0faeaf8fbb047d902d00590b70fb77a39a5899c0c4939f9efa69e0aa855d`、game4off `0112a83f2dbaab24a5c006f44bed84693c5bd0a6c70a9714c39dbcf662cfad1c`、game4fixed `6594c881726b554ea98edcfbd49cb35204632d66779f3b9f4c27ef63bfa0daec`）分别CRC33/33/41 PASS并原manifest同源。Game2/4真TLS2/4 lane、OS Applied内MTU1373（Fixed1358）、Linux+Windows真双向UDP、Windows kernel client→Linux TUN server TCP echo **成功**，产品最后`M0_PLAN027_GAME_STOP_RESULT stage=product_stop result=PASS`、`WBD_WINDOWS_GAME_NATIVE_DISCONNECTED ... wal_restored=1 rust_stopped=1`。未能到达验证器正常Stop字段，因通用`tcp-functional.py`另外要求 Linux 主动建立到Windows Wintun:45902 的独立反向入站TCP，Windows server_received=0 / Linux client_echo=false，先失败。这是旧028独立入站测试边界，本次只证明其未成立，**不宣布反向入站可用**。

按Game用户要求仅修正测试*资格*：对本Game2/4四job ×五真实业务策略，采用已有H1762原生 **Windows→Linux 真Winsock/TUN TCP建立、跨内核收发/echo+Linux真实服务器received_bytes**，同时继续强制双端真正UDP、物理LAN、普通CN/高级CN DNS+FakeIP/Direct TCP32768B+UDP、同源TLS/FEC/OS/每腿Rust Stop/WAL/进程退出；留痕 `legacy_028_linux_initiated_windows_tcp=NOT_RUN_SCOPE_SEPARATE`。其他Normal、旧Game4和028严格双向TCP校验完全不变。仅本Game矩阵的后端PowerShell收口按同源真实TCP+Stop严门，不能宽松接受字符串伪造。

**候选原生全20组合未通过前仍NOT_RUN/FAIL**, 原H2158与所有旧红Action保留；不改生产Go/Rust/FEC/wire，也不拿旧Game4成功回执借绿。

```feature-impact
{"kind":"none","ids":[],"reason":"H2159 isolates historical PLAN028 Linux-initiated inbound TCP comparator from new Game2/4 split-policy tests, preserves real Windows-initiated kernel Tunnel TCP+Linux echo, UDP and owned Stop and all other strict gates; no runtime change."}
```
