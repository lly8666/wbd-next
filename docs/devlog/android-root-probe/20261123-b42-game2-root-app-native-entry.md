# B42｜原 Game2/off 正式 Root App 入口接线

接续 B41 已编译原 Go 双 FakeTCP/标准TLS、受保护同epoch Game2 group、原 Rust 单TUN双RAW M3/M4、UID与Stop。本批只将正式Root App显式Game2/off模式、预设保存/恢复、START Intent、Service和原 Go argv连通，不新增Java/Go逐包、Rust协议/安全框架。Go `--game-fec` 默认off，Game4、Game FEC和Game2 App DNS仍不开放。

选择Game2时关闭原默认隧道/物理/CN App DNS及startup padding；Activity、Service和生产Go argv对齐，旧Normal/Fixed/Auto与预设格式不变。现有Host JVM测试覆盖Game2预设及原Go实际参数，也保留不支持的DNS组合拒绝。GitHub Actions未完成前仅称WIRED_CANDIDATE；当前SOURCE的双ABI、签名APK、Linux Oracle需按新Action单列判定，实体双lane TLS/M4/TUN/UID/Stop与性能NOT_RUN。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B42原Go Game2/off双TLS→Rust M4在正式Root App模式、预设、Service、argv全链接线；不增加安全或数据面。"}
```

## B42a｜修正两处历史模式列表源码门

旧 `test-network-scope-gate.sh` B41/B19仍要求正式App恰好三模式，与B42真实Game2/off接线矛盾。本批只改两处旧模式列表断言为四模式，并补真实Activity→Service→Go argv→Preset的源码接线检查；B41两lane TLS、原Rust M4及Stop门保留。B42首次SOURCE若因此失败必须保留，不冒称当前构建PASS。
