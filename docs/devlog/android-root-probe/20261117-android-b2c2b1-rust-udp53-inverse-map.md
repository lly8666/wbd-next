# B2c2b1 — 原Rust DNS53 单一 Tunnel 交易五元组反向映射与IPv4/UDP校验和（2026-11-17）

分支 `experiment/android-temp-root-probe`；上个证据 HEAD `d0ebd80f413a02fde66a9916d5eec625292a5f2f`，Draft PR #36。禁止触碰main/M0/旧Linux Windows协议/实体KSU/云购买。

## 产物和安全界限

新增 `crates/wbd-engine/src/v4_android_dns_udp_flow.rs` 作为**原Rust引擎模块**（`lib.rs` Android ARM64正式构建和host测试可见），不是Go/Java逐包泵或第二个TUN fd。采用每代64个定长、过期12秒的纯Rust UDP53交易槽，唯一synthetic源端口范围50000..50063，保留原App的IPv4源、临时UDP端口、原DNS目标IP和原DNS ID/QNAME/QTYPE/IN规范化问题；对合法完整非分片IPv4 UDP DNS问句可重写目的为固定Tunnel `1.1.1.1:53` 和专属端口，对**已经由原WBD M1/M3 AEAD/重放鉴别的**对端回答，在同样本机源/port/ID/QNAME正确时把源IP恢复为原App的DNS目标，目的端口恢复为App源port，自动重算IPv4首部和UDP伪头/数据校验和。UDP checksum=0被当做不允许省略的结果，换为0xffff。无DNS wire FakeIP/补造Answer，无系统netd副作用。

容量满、交易已过期、其它目的端口、错误源DNS/IP、恶意ID/QNAME、首/后IPv4分片、错误IP总长/UDP长度、畸形问题立即拒绝且不修改原Packet；同问重传重用槽，Stop清空全部槽。所有UDP53包仍在B2c2a原M4**透明传输**：新模块刻意还没有被`tun_worker`调用也未装入RX写TUN前的authenticated inverse hook，`hijack_enabled=0` 保持硬门。目的只是先证明双向源/dst/port及校验和的基础资格，再让双物理/Tunnel backend与Rust Rx/Stop、系统Resolver真实受控启动同时入Owner；不允许只做单向DNAT造成答复失配/互联网泄露。

新增Actions独立`b2c2b-rust-dns-udp-inverse-map` Rust Host真完整IPv4/UDP报文字节/IPv4和UDP伪头校验和正反验证、恶意响应、QNAME大小写、重传、64项上界/12秒/Stop、分片/畸形零改包；原Android ARM64 Rust+Go同源ELF、签名APK、CN8503、Host真socket、原Linux TLS/租约/M4双向UDP/Stop oracle全量回归。这些仍**不是**真实设备DNS E2E/原TUN DNS数据包映射通过、Android P2/P3成功。

## 验收分层

初始SOURCE未经过Actions，不宣称测试通过。符合 `B2C2B1_ORIGINAL_RUST_UDP_DNS_INVERSE_PACKET_HOST_PASS`后也只等同于Rust纯报文转换/映射证明，不是签名App→root→netd或原服务端隧道DNS。托管ARM64缺可访问的/dev/kvm，P2/P3 ENV_BLOCKED，实体KernelSU P5最后需专项用户授权。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B2c2b1原Rust引擎同源固定64项UDP53问答五元组/ID/QNAME反向映射与IPv4 UDP校验和完整包测试；原M4保持不劫持无第二TUN读者，Android真正DNS仍未接。"}
```

## 首轮同源测试的负例夹具失败（保留历史）

SOURCE `1288f1f714f6fc9a1f2e732b077ba3e455da6b25` [Action44090496300](https://github.com/lly8666/wbd-next/actions/runs/44090496300)，B2c2b1真实完整IPv4/UDP packet的双向反向映射、checksum、ID/QNAME防串答、64槽容量/Stop三项Rust Host测试PASS；第四项`b2c2b1_rust_udp53_rejects_fragments_and_malformed_without_packet_mutation` FAIL，原因是畸形长度测试把`p[24]`（UDP长度**高字节、本来就是0**）再次设0，报文本身完全合法，所以产品候选正确接受为`Ok(())`。只将该负例改为`p[25]=0`（实际原UDP长度低字节非0、必须被拒绝），不改变解析/映射实现。前一Action的FAIL如实保留；必须新SOURCE重新跑全套Actions，不使用旧Native/APK/Linux工件代替同源证据。

**路径触发补充**：夹具修正SOURCE `fb2f1ca2038d22362f7c1cfdd6065d3760e4d873` 通过governance但旧产品工作流paths不包含新增`crates/wbd-engine/src/v4_android_dns_udp_flow.rs`，因此**没有触发新产品测试**。本次改`android/root-native/ci/dns-b2c2b-rust-udp-map-host.sh`（已包含在产品workflow路径）同时强制检查真正破坏UDP长度低字节的负例；新SOURCE将实跑整套Jobs，不把单独governance success当软件PASS。
