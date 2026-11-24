# B89｜Android接线集中验收，不再做性能测试

B88 SOURCE `5a286b6bfa9f6094e24d2d162ccf097d116a2d0c` [Action 45401336748](https://github.com/lly8666/wbd-next/actions/runs/45401336748) 6 SUCCESS / 1 FAILURE / 10 SKIPPED。构建失败为 PLAN030 Linux management_snapshot_linux.go 在 GOOS=android（同时满足 linux build tag）引用仅 Linux/FEC build 的 V4LinuxGameCohortID。B89对三份 Linux 服务管理文件加 !android，Android只保留共享入口的冷编译适配；手机不接入服务器管理。修正H2408 SYN/TLS独立期限的过期静态测试。B88治理/维护亦失败：main H2409 M0 cursor last_tested_source 与既有 evidence_refs 不一致，保留真实红灯，不修改M0 cursor或放宽治理。B88性能矩阵在依赖失败后SKIPPED，不重跑。

用户新指令：不做性能测试，其他平台既有结果保留，集中实际Android接线、尽可能复查A48真实ARM64 Normal/off历史通路与其余六模式差异。A48真机原认证、/32、双向M4及Stop曾通过，非最新源性能或全部模式验收。B89使用一个 Android16 x86 KSU boot、一个原Linux shared server、同源CI-only APK，连续七种模式 Normal/off、Fixed6、Auto、Game2/off、Game2/Fixed6、Game4/off、Game4/Fixed6，默认无附加DNS/outer repair，TLS证书验证OFF符合真实产品默认。实际生产RootService发出参数、Go实际解析mode/profile/lanes与预期匹配、真实TUN、首个已绑定RAW和SYN sendto（Game此时只有首lane，不声称全部lane），每模式通过原Stop、等待owner结束、核查TUN消失和原RST规则/日志无残留。未清理不强行重启。独立CI Bionic Go真实TLS/admission测试二进制（同源、原关联夹具，非APK），在相同Android guest运行既有Normal各FEC、mixed Normal/Game、Game冷组、epoch和FEC wire/证书测试。Host只跑原真实TLS/Android Rust lane mapping/A48-A49 parser等接线功能测试，不跑Linux live dataplane及十四场景性能矩阵。标准正式ARM64 APK、原Go/Rust ABI、DNS等现有构建门保留。所有新SOURCE结果待CI，SLIRP/TAP不重开，真机全部模式认证/UID业务/M4和完整Stop不能从模拟推断。

复查重点：Normal三模式共享原Go/Linux client product和Bionic Rust direct TUN/RAW，Game独立原Go冷组→真实2/4 Rust group接管，沿用相同TLS admission、MSS/MTU预算、A48 Android TCP checksum pending→原M3，以及真实UID路由/Stop。Game首RAW/SYN日志只在实际绑定/发出成功后各一次，无新增数据面检查。不加防御、FakeIP、热迁移或替代协议。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Fix real B88 Android build isolation, switch to user-requested wiring-only validation with seven real KSU preauth/cleanup modes and independent Bionic original TLS tests; no performance runs."}
```
