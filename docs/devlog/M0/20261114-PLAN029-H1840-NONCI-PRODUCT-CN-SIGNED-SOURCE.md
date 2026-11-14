# PLAN029 H1840｜独立真实用户入口：禁CI试验门后，签名Normal CN Direct+Tunnel与owned Stop

- H1838 [Action43593580875](https://github.com/lly8666/wbd-next/actions/runs/43593580875) 在真实编译的WinForms→便携配置保存/导入→当次原Go`--check-config`完整通过，但它**不能**证明用户真正点击Connect后Windows OS路由、真实CN DNS/TCP/UDP、Rust NativeOwner和Stop。
- H1832已实现正式默认关闭的`--split-enable`及`--cn-rules-file`；从非Actions的普通程序启动应读同一个冷source。之前H1831原真Windows D3场景仍带`WBD_PLAN029_NATIVE_V3_TRIAL=1`/Actions试验环境；测试产品正式开关必须彻底避免借这个门，**独立源锁Action**。
- H1840仅扩现有`m0_wl_public_normal_e2e.py`的`WBD_PLAN029_PRODUCT_SPLIT_SCENE`：保持真实原Go TLS、签名Npcap/Wintun、同一Rust `NativeSplitWorker`、Linux原TUN/physical app及原owned WAL/Stop；按现有Direct单场源配置使用**`--split-enable --cn-rules-file <本场owned绝对域名文件>`**。仅子进程显式设`GITHUB_ACTIONS=false`、`WBD_PLAN029_NATIVE_V3_TRIAL=0`，删除CI旧`WBD_PLAN029_CN_RULES_FILE`环境变量，保证它真的是原Go产品冷配置而非试验兜底。新scene仍Normal一lane，Game4 CN没接会冷拒绝，不误报正常游戏分流。
- H1840由新的单独标记`[plan029-real-product-cn]`触发，`tools/m0_native_ci_scope.py`及原workflow env限定在main push；`WBD_PLAN029_V3_DIRECT_SCENE=1`复用现有当前源原Windows/Ubuntu真实业务验收且外层默认1460，**不**同时启动P2/D3 multiA或028全矩阵。真实`WBD_WINDOWS_OS_APPLIED`和`source=explicit_config readiness=AWAIT_REAL_OS_RUST_RECEIPT`顺序须出现在原Go日志；真实Windows+Linux UDP/TCP业务和已归档D1/D2单DNS负测要保持原断言，最终验证`M0_PLAN027_NATIVE_STOP_RESULT ... PASS`、route WAL与Defender listener sidecar均真正不存在。e2e写完整`plan029_real_product_normal_cn`收据，工作流再校验SOURCE/effective/Stop。没有虚假GUI按钮点击、无Go packet pump、没有新WFP。
- H1839另一路真签名P2 Actions已在SRC `a50f8c5`准备；本H1840 **没有P2 marker**，只触发一条不同SOURCE的产品入口场景。H1840 SOURCE签名真实网络**NOT_RUN**直到Action终态，不能因为场景源提交就当产品验收通过。后续本次场景通过也只是CLI真实出口，GUI**用户实际点击**Connect/Stop和Game4/IPv6/P1/P2/慢fsync仍OPEN。
- H1837真实P2超38s且Linux完整1MiB收/发已保留在`docs/evidence/M0/PLAN029-H1839-H1837-P2-SIGNED-ONE-MIB-DOWNLINK-TIMEOUT-20261114.json`。下一步先核真P2相位与Rust双腿收据，而不是调10ms已有活跃TCP等待。

```feature-impact
{"kind":"none","ids":[],"reason":"Add one exact-source signed non-CI product cold CN split activation and native OS/Stop witness using existing Go CLI, Rust owner and Wintun; no new production behavior/config schema."}
```
