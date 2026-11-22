# B39｜原Game2/4 Rust冷组与Android每lane真实RAW绑定（M4尚未安装）

## 本批已施工的生产层，而非模式按钮

Linux原Game2/4拥有完整已保护Go TLS lane → Native GameAdapter → 独立raw RX/TX → 单TUN Rust M4。此前Android虽然以 `fec2_product_record` 编入 `game_group_join_original` 的crypto-only C接口，但没有将来自**同一Android用户选定物理Network**的真实已认证原Go Game lane的原始5元组/原TX、RX boundary规范成组，也没有Android独立的per-lane RAW Bionic套接字拥有者。

本批将Android版本的验证放入**真正的原Rust `game_group_join_original`**：2/4条原Go已提交TLS/M1的handle、独立原lane ID、原server 443端点、严格不同且连续的client FakeTCP端口、相同客户端IPv4、原Go真实TX boundary、相同Network handle/ifindex/MTU/interface与保护租约必须一致，拒绝与Normal已有原M4 raw/TUN worker的冲突。原 GameAdapter AEAD/PN/FEC构造和 `game_group_state` 继续保留，不创建第二套密钥或cipher。

在单独的原生冷接线 `wbd_m0_embedded_go_android_game_group_raw_bind` 中，按已认证组的每lane五元组复用平台现有 `AndroidBoundRawRx::open_exact` 与 `AndroidBoundRawTx::open`，每个RAW fd必须经过Android Network绑定、接口/MTU核对及精确BPF。耗时内核绑定在全局组注册锁外进行，Stop并发则不发布任何新FD；绑定状态单独 `...raw_state` 只返回实际持有的FD数。组Stop先停RX/TX借用、确认Drain，再Stop同一 `GameAdapter`，原Go TLS逐lane release仍是另一独立阶段。Linux及Windows现有Game产品路径/传输格式不改变。

Rust host纯单元测试在相同原生产规范化函数上检查乱序2/4lane、重复/缺失/交叉物理tuple、非连续端口、无效TX boundary。Android ARM64和x86_64真实Rust .so ELF要求 `game_group_join/state/raw_bind/raw_state/stop` 符号；Host源码门追踪到真正Bionic RAW方法。所有测试/资格必须来自**B39新SOURCE**；未产生Android Game应用吞吐、服务端Game ACK、真实TUN delivery或证明机器耗电改善。

## 后续必须真实施工

下一批实现Android Game2真实Rust **单一 TUN M4 read→GameAdapter→按lane RAW TX** 与并行 **各lane RAW RX→M3 AEAD/PN→同一TUN write**，同时接原Go两条独立FakeTCP/标准TLS冷控制与现有Root UID路由；Stop必须同步drain组级RAW+TUN，再释放每lane Go原Owner。只有实际正反向业务包、设备/服务器验收才解除原App/CLI的Game拒绝条件。Game4必须等Game2真路径先通，不得删拒绝门制造假接线。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B39原Rust Go-TLS Game2/4冷组建立同一Android物理Network和每lane真实Bionic RAW RX/TX owner，保留M4未接和Game模式拒绝。"}
```

## B39a 编译与跨平台回归修订（初版失败必须保留）

初版 `796c45863599`：Rust Game2/4 original host单测SUCCESS；真实Android双ABI `arm64-native` FAIL，原因是Git Tree同文件分阶段覆盖，Rust `GameGroupNative` Android scope/raw字段、`AndroidGameRawLane`类型与 `canonical_original_game_lanes` 调用未进入最终源码。当前B39a在一个文件内重新合并这些生产代码，同时强化Android根App源门核查这些字段。独立maintenance regression的旧PLAN029静态测试只允许Windows/Linux `v4_client_split` 和 `v4_client_startup_padding`，与先前Android已编译路径不符；仅更新其目标平台枚举，未弱化任何协议断言或移除测试。是否彻底通过，以本修复新SOURCE Actions为准。无设备/Game流量PASS。
