# A19b：原 x86 Linux 服务端/客户端 + Rust D2-S0 主机门真实 PASS（2026-11-18）

**真实 SOURCE `4952442ab813ef41558ca3308793c330213c89d9`**：[GitHub Actions #44238444687](https://github.com/lly8666/wbd-next/actions/runs/44238444687) 中新增的 `linux-x86-original-server-d2-s0` Job `SUCCESS`。官方 Artifact **#14398019021** 的 `manifest.json/SHA256SUMS/elf-server.txt` 已独立核对：`original_linux_server_cli_helps=PASS_REAL_LINUX_EXECUTED`，`linux_arch=amd64`，`android_ci_abi=x86_64`，固定原 Go donor `a7a82db31fe736ffedee330795a3234d358f1984`，原 Linux Go server/client 和 Rust `libwbd_engine.so` 三份 x86-64 ELF/SHA 锁定同一个 Android 原 Go/Rust SOURCE；`--help` 为真实 Linux ELF 执行，不是简单 cross-compile。

同 SOURCE 的 D0 ARM64/x86 原 Android Go/Rust 构建、ARM64 签名 APK、原 Linux ARM64 真协议 oracle 也各自 SUCCESS；x86 Android 普通 App UID→真实 KSU su、同一 `PhysicalNetwork` 精确网络读回的前序 PASS 证据见 [Action44236693889](https://github.com/lly8666/wbd-next/actions/runs/44236693889)。历史 ARM64-on-x86 NativeBridge ELF139 红门是另一个手动诊断，不是新 x86 原生产品失败。

**严格验收边界**：D2-S0 只是主机侧原服务端和 CLI 已经同源装配/真实启动。官方清单明确 `original_server_authenticated_session=NOT_RUN`、`android_x86_real_tls_lease=NOT_RUN`、`android_original_m4_tcp_udp=NOT_RUN`、`android_owned_stop=NOT_RUN`、`system_dns_takeover=NOT_RUN`。下一关需要同一 Actions host 上启动实际原 Linux server 的临时隔离凭据会话，经普通 Android App 调用生产 `RootClientService` 执行 TLS/auth/自动 /32→Rust M4/双向 TCP+UDP→原 owned Stop；绝不允许 Help/单 UDP 包升级为业务 PASS。所有密钥作业内生成、0600、不上传。系统 DNS 冷许可 false；ARM64 仅正式发行，实验分支 PR #36 Draft，不改 main/M0。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A19b 登记原 Linux x86 服务端/客户端及 Rust 同 SOURCE 真实 ELF 与 CLI D2-S0 PASS；Android TLS/M4/真实数据/Stop/DNS 仍 NOT_RUN，不用 server Help 伪造 Android E2E。"}
```
