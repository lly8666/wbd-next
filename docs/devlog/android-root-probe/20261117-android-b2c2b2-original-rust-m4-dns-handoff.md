# B2c2b2 — 原Android Rust M4 TX/认证RX/Stop 同代DNS53双向接线（2026-11-17）

**远端开工HEAD** `460bb64d89308ad7f365520e1f918817cf10e549`（Action #44094853288 同源10/10 SUCCESS）；main 开工HEAD `71f6756a6c04adf1ad0f7334b11d1be3d77be1b8`。只提交 `experiment/android-temp-root-probe`，Draft PR #36；main M0/registry/cursor无修改。只审远端已提交代码，无远端worktree，不能宣称查过未提交本地修改。

## 这批实装（不是又做单独探针）

- 在原 `Entry` 添加同代、固定64槽 Rust `TunnelDnsUdpFlows`；同一Rust M4唯一TUN `read_ip_scatter` 后，已认证租约/IPv4完整检查通过的普通小包直接在原M1 slab上重写候选UDP53；超过单帧预算的DNS走原完整IP的M3 jumbo后重写，再由原AEAD/PN/MTU/RAW发送。没有第二数据面、Java/Go逐包、伪TLS或假IP。
- 原 `ProtectedScopedOwner::drain_android_normal_off_to_tun` 已经由原AEAD/唯一PN和M3完整重组认可业务后、原唯一 `write_authenticated_ip` 之前，增加仅对 `1.1.1.1:53` 与当前64槽反向端口的回复候选进行逆映射。一次预分配最多4164B的Rust RX scratch，只有候选回复才复制；不合法/过期/伪造候选fail-closed，不回落写原目的DNS，也不篡改独立普通业务。Go原TLS/认证/租约与Linux路径保持原样。
- Rust原 `stop` 先唤醒/join真实M4线程，再清空同代所有DNS交易槽并撤销接管许可，然后退役原Rust密码owner和RAW/TUN借用FD；早期已认证的M3缓冲同样进入受控RX hook。
- **安全准入保持冷关闭**：`android_dns_hijack_ready:false`，无可对外开启的API，`wbd_m0_embedded_go_loop_dns_ingress_observed`仍报告 `hijack_enabled=0`。未完成真实物理223.5.5.5及Tunnel1.1.1.1双DNS、CN域名冷分类、TCP53和Android netd Resolver证据前，M4还是透明正常DATA。没有新探针按钮。

## 同SOURCE验收与停止

原B2c2b Host4项保留，新增1项合法UDP53来源/原生临时端口过滤与真实包反写；现有Source gate要求真正M4 TX短包+jumbo、原authenticated RX逆映射、Stop都同代连通且`hijack_enabled=0`。该SOURCE第一次提交前 **NOT_RUN**；只以新SHA Actions全套Android ARM64原Go+Rust Bionic ELF/16KiB、签名APK、B1/B2/B2c主机、原Linux server真TLS/租约/M4双向UDP/Stop oracle裁决，保留原坏夹具FAIL。Host/source/跨编译≠Android guest/实体KSU实际查询。P2/P3 ARM64 KVM依旧ENV_BLOCKED；P5实体设备不得在未授权时运行。

**唯一下一步**：在一个大批内补齐同owner的物理CN DNS/隧道DNS真实后端和CN规则冷入口、TCP53与Android系统Resolver owned接线，取得同源可运行环境后再授权开启劫持；不单独启动孤立新合成探针。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B2c2b2原Rust M4唯一TUN TX短包/jumbo与原AEAD/M3 authenticated RX实际UDP DNS53映射hook、同代Stop；冷许可仍false且hijack=0，无Android物理双DNS真实运行声称。"}
```

## 首轮SOURCE结果与一次测试选择修复（保留失败）

原代码SOURCE `686c6257e12f28fb4ad06cfafea16c3859cd536b` 的 [Android产品Action #44097311545](https://github.com/lly8666/wbd-next/actions/runs/44097311545)：Rust B2c2b1四项均PASS，但新增B2c2b2命名测试没有被旧`cargo test --lib b2c2b1_rust_udp53`过滤器选择，Host脚本要求5项因此**FAIL**；这是测试覆盖选择缺口，不是观测到产品数据包读写错误。其他已完成Job中ARM64 Bionic原Go/Rust完整构建及正式签名Root APK PASS，Linux oracle是否通过由Action最终结论裁决。既有FAIL照旧保留。

本次仅将Rust Host过滤器扩大为`b2c2b`，覆盖旧4项和新增第5项；不修改产品M4/AEAD/RAW/TUN/NAT。必须在新SOURCE重跑全部产品Actions；新的同源结论在Actions完成前仍 **NOT_RUN**。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"记录B2c2b2首轮Rust Host过滤器只跑旧4项导致第5项漏选FAIL；修正SOURCE测试选择为完整B2c2b五项，不改原Rust生产数据路径。"}
```
