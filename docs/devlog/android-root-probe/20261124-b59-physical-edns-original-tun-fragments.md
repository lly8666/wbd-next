# B59｜原Android物理DNS EDNS大应答按真实TUN MTU分片

**上个合格SOURCE**：B58a `452302f11c0a90c6aadcb6403d1edb2041272e1a` [Dual64 #45209186326](https://github.com/lly8666/wbd-next/actions/runs/45209186326) **11 SUCCESS / 4 SKIPPED**；B58b `4d03f1e5f596fe59649681320fbd82b803df5fc4` [治理 #45210124110](https://github.com/lly8666/wbd-next/actions/runs/45210124110) SUCCESS。实体手机和Android↔Linux逐字节E2E仍NOT_RUN。

## 真实功能缺口

现有唯一原Rust M4物理UDP53从所选Network绑定socket接收至多4096B EDNS DNS wire，`PhysicalDnsUdpFlows.receive` 在确认原App IPv4/UDP源端口、解析器、合成DNS ID、QNAME和真实回复后构造有IPv4/UDP校验和的真实回复（最大4124B）。此前 Normal和Game都一次把这个完整IPv4写进原TUN，不根据本会话原定的inner MTU处理超过MTU的大TXT/EDNS应答。

## 本批原生接线

1. `v4_android_dns_physical_flow.rs` 新增纯Rust有界输出 `emit_physical_dns_tun_reply`：先验证已合成单份物理DNS回复，若不超过inner MTU仍一次原样写；超过则暂清DF并重算IPv4头校验和，复用原B16 RFC791 `v4_android_ipv4_mtu::fragment`、8字节偏移/MF与原IPv4 ID，最多128次写出；无论成功或失败都恢复原包DF/校验和，没有新DNS/TCP解析器、Go packet热路径或追加线程。
2. `android_root_io.rs` 在原`AndroidOwnedTun`上增一个fragment写入入口，使用同一FD/BorrowFence、Stop与代际读回；首片必须含源端口53，后续碎片无UDP头而按有效片偏移/长度处理。所有物理DNS片段仅由现有bound DNS socket、ID/QNAME逆映射、原客户端/32租约验证后的唯一TX线程调用，并非远端认证M3数据写入。
3. Normal/Fixed/Auto与Game2/4原worker各增加一块2048B复用scratch，把物理大答输出为多个同TUN内层IPv4，只有全部片写入成功才计一次原`physical_rx`；失败记`physical_errors`。原TCP53仍原M3透传，原Go TLS/租约、私有UID表和Restored Stop一律不改。
4. 同SOURCE已有 Rust DNS Host Job新增完整EDNS(OPT)和大TXT答复、UDP原校验和、MTU576/1260/1460逐片IP头/offset/MF及重组等价；小包原1次write、第二片写失败不计完成，原包状态还原；原Root App源码门和双ABI/签名APK/Linux原服务端Oracle继续采用原Dual64 Job。没有新工作流或KVM/实体设备动作。

**严格边界**：CI只确认原Rust Host和源锁Android ARM64编译/装配，不宣称Android实体内核重组已验证。系统netd/DoH/Private DNS和物理TCP53未接线，普通TCP53仍走原M1/M3。实体App DNS/业务/性能仍为NOT_RUN/NOT_PROVEN。仅更新实验分支，Draft PR #36 保留。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B59原Rust Normal/Game物理DNS EDNS大IPv4通过B16相同TUN分片返回App，补齐超过inner MTU的大DNS答案；真实Id/QNAME/原租约、Stop、Go/TLS和原TCP53不变。"}
```
