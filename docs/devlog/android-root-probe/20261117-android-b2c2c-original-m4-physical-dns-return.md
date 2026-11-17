# B2c2c 原Rust M4单就绪线程物理 DNS53 socket 与同TUN逆回包（2026-11-17）

远端开工分支SOURCE `c9d7931443e5f5830e879a5ff561337ded0f8922`，main开工 `44ea3189728548117b543dac7940a69710feca21`。只动 `experiment/android-temp-root-probe` 与 Draft PR #36；main/M0/registry/cursor不改。最近同源码B2c3 [Action44102216916](https://github.com/lly8666/wbd-next/actions/runs/44102216916) 10/10产品PASS、[governance44103094849](https://github.com/lly8666/wbd-next/actions/runs/44103094849) PASS；不借旧SHA为新改动背书。无远端未提交worktree可查。

## 真正的单-owner代码纵切面

- `wbd-platform::android_root_io::AndroidBoundPhysicalDnsUdp`：真实 ARM64 Bionic非阻塞UDP53 socket，经 Go认证generation、被选定Network handle、ifindex/MTU和原IPv4，原生`android_setsocknetwork`+SO_BINDTODEVICE及同fd的设备+local IPv4读回，connect仅国内物理`223.5.5.5:53`，无全Root fwmark/默认网回退；原BorrowFence+Stop。
- Rust `PhysicalDnsUdpFlows`：64槽/12秒，原M4唯一TUN readv的真实IPv4/UDP53 DNS query→一条真实DNS wire和 synthetic ID；原连接socket收包后原问题 ID/QNAME/有效槽检验，还原原DNS服务器IP/原App端口/租约目的IPv4、重算IP+UDP checksum，组出可以写回原内核TUN的IPv4报文；Host用真实IPv4/UDP bytes测回程/错误/Stop。无FakeIP/伪ACK。物理DNS不是远端WBD认证消息，严禁调用原AEAD authenticated sink。
- 同原M4 TX worker同一个eventfd poll同时监听TUN与物理UDP FD（上限8条/turn），小包直接原M1 slab及单readv jumbo两条路径都可走物理DNS；socket发送失败清交易、无偷偷走隧道。物理回包只由此worker写**同一个原TUN BorrowFence fd**；原远端WBD RX依旧必须AEAD/唯一PN/M3完整后才交原authenticated writer；原Stop先join线程，物理交易表清零、FD关闭后才退役原M1/M3。
- **冷许可仍严格关闭**：`android_dns_hijack_ready:false`、`android_dns_physical_ready:false`，真实App仍普通WBD正常DATA、指标`hijack_enabled=0`。原Go CN8503完整 QNAME 路由还未安全传到Rust，此处没有授权所有DNS都发到物理网；物理TCP53/同目的TC回退、Android系统Resolver入场、Tunnel TCP53同样尚未接线，严禁说DNS已工作。
- 本批新增两项Rust物理真实包 Host/Stop回归，更新同源码完整ARM64 Go/Rust Bionic、签名APK、原Linux Go/Rust server真TLS/租约/UDP/Stop Action门和功能卡。**本SOURCE提交前运行NOT_RUN**；P2/P3 Android16 ARM64 KVM不可访问，P5 KernelSU无明确部署授权，不能声称模拟器/真机验收。

唯一下一步：在原Go8503经认证冷策略和原Rust M4一次性连接后，完成物理/隧道DNS TCP53及系统Resolver ownership；仍以Android16真实可执行环境 E2E做最后准入，不增加重型极端工况测试矩阵。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B2c2c原Android Rust M4唯一TX worker/TUN整合真实Bionic物理UDP DNS53 fd、同fd读回/64槽DNS逆IP/Stop和两个Host原包测试；DNS仍保持冷关闭。"}
```

## 首次同SOURCE门失败记录与一次性修正

原代码SOURCE `71565fd189b0cbff63358f480e1da14388a7af6f` [Android产品Action44107830995](https://github.com/lly8666/wbd-next/actions/runs/44107830995)：`cargo test --lib b2c2b` 实际 **7/7 PASS**（新增 `v4_android_dns_physical_flow::tests::b2c2b3_...` 两项也PASS），而Host Python枚举使用旧`v4_android_dns_udp_flow`固定模块路径错误，导致 **b2c2b Rust Host Job FAIL**；这是报告器定位错误，不是已观察到Rust报文校验和逻辑失败。ARM64原Go/Rust native构建PASS，其余Job以Actions最终状态为准。历史FAIL永久保留。

本次仅根据测试真实路径将两项新模块列入报告器；原Rust M4、Bionic socket、TUN返回、原TLS/lease/AEAD/Stop产品代码一字不改，仍`hijack_enabled=0`和`android_dns_physical_ready=false`。新代码SHA全套产品与治理Actions必须独立通过，提交前为 **NOT_RUN**。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"记录B2c2c首轮Host收集器旧module路径错误FAIL（Rust真7项PASS），修复新物理DNS模块测试路径；不动原M4/NDK生产代码。"}
```

## 同源码物理socket精确设备名称绑定纠正

在源码合并验收前将物理DNS新socket的`SO_BINDTODEVICE`同FD读回，从仅比较接口名称前缀改为完整名称加NUL终止校验（`wlan0`不能匹配`wlan0x`）。这属于Bionic真实物理作用域的必要产品正确性，不改通用M0或任何既有Go/TLS/M1/M3/健康协议。完整同SHA原Android ARM64构建负责验证ABI，设备实际内核readback仍为**NOT_RUN**；第一版`71565fd` Host误判仍保留。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"纠正B2c2c物理DNS的Android SO_BINDTODEVICE读回必须完整名称匹配；随Host新模块定位修复整包验证，旧FAIL保留。"}
```
