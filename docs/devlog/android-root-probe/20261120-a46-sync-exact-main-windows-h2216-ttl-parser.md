# A46｜把 main Windows 已修复的 H2216 原生 IPv4 TTL 解析器同步到 Android 实验分支

## 本次真实证据与用户限制

用户 API36 安装 SOURCE `bd524c209137a7bd7c1196e8ab65fd371fd85f5e`（A45）选中 Chrome 和 ping 工具实测仍不通，诊断两次均 `ORIGINAL_GO_UID_ROUTE_GET_MATCHED_TUN`、原 Rust `TUN_IPV4_SEEN` 和 `APP_RAW_TX_COPIED`；首轮同时有真实 TUN ICMP/TCP/UDP，手机 RAW socket 出现 `RAW_SOCKET_READABLE` 与 `RAW_PARSE_FAILED`，但没有 `RAW_PARSED` 或 `APP_REVERSE_TUN_WRITTEN`。纯 ACK 或其他非业务TCP也可能触发宽泛的 RAW_PARSE_FAILED，不能把每一次该事件归责为业务解密。两次原 owned Stop 均过。用户明确指出：**公网 Linux 服务端与已修复 Windows 客户端长期正常双向传输**，故本轮不猜公网服务器/NAT故障，也不复验 TTL 原理；只移植主线已验证修复。

## 根因：分支未同步已落地的 main H2216

对照 main 当前 SOURCE `ad6bef638faf0075e1923d2a97849dc255e6877a`，Windows 公网路由 TTL 修复已经于 main 的 H2216 落地，基线 commit `f396f1fb2d49af530f53ccd18ce3ac60b1a89d77`、后续 `5774edc8ae1cfc8565b74309bbbb58e0a2d048d7`、回归整理 `91b9d521ce1451300533d078844340add4820c29`。原 `crates/wbd-platform/src/rx_ipv4_tcp.rs` 同时覆盖 DATA 和可选纯 ACK：拒绝 zero TTL 而不把 sender Persona 的 TTL 原值当端到端身份依据；原IPv4/TCP校验和、四元组、选项、DF/MTU，及其后的 M3 AEAD/PN/replay 不变。官方主线测试 `h2216_original_windows_128_to_116_client_public_nat_data_and_ack` 固定覆盖 Windows11 128→116、Legacy 64→52，路由器重算IP checksum、zero TTL和checksum畸形负例。

实验 Android SOURCE A45 的同一个模块**仍是旧版**，要求 `packet[8] == trusted.persona.ttl()`；在真实互联网经过多跳后，这将拒绝合法原Rust M4 DATA 和 ACK、阻断加密业务，不能通过继续只增加日志修复。经逐行差异检查，当前实验文件相对 main 除 H2216 头注释、DATA/ACK两处判断、原测试修正、新 H2216 回归测试外无其他差异。因此本次 **整文件直接拷贝 main 已落地版本**，没有独立重新实现或放宽 AEAD。Android 原Rust `AndroidBoundRawRx::read_original_record` 直接调用此共享 `rx_ipv4_tcp::parse_data_packet`；现有唯一原Rust M4 / Go/Rust接线均不改。

## main Linux 客户端已同步，无需重复 PR

已查主线 `crates/wbd-platform/src/linux_raw_carrier.rs`：单包、multi-buffer 及Linux收包的 DATA 和 ACK 使用**完全同一 `rx_ipv4_tcp` 模块**，主线 parser 已包含 H2216。按用户的条件“main Linux 若未修复才开 PR”，检查结果**已修复**，所以不创建无改动PR，不碰 main；本次只动 `experiment/android-temp-root-probe`，PR #36 仍 Draft。

## 回归与边界

在原 Android source-locked门上核 exact DATA/ACK修复、H2216原测试、Android真实原Rust RAW依赖、Linux共享接入，并在真Linux ARM64 Oracle 上运行 **主线原生 H2216 Rust 测试**（不是新手工复刻），再保留原 Linux Normal/off真实TLS+Rust M4+UDP/Stop oracle和原签名 ARM64 APK、FeatureCatalog。源同步、编译和 Host oracle PASS 不等于 Android Chrome/ping 已恢复；用户下一次实测要见到来自真实业务后的 `RAW_PARSED`，并最终 `APP_REVERSE_TUN_WRITTEN` 与独立应用成功；若仍未通，再审剩余客户端接线/原服务端M4差异，不回退安全门、不强推全局。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A45真机RAW解析失败且没有反向M4；直接同步已落地main Windows H2216严格但路由兼容的DATA/ACK TTL修复与真实主线测试；main Linux已经复用同一parser故无需新PR。"}
```
