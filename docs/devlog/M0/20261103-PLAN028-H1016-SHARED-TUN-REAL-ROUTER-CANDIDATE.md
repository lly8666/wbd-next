# H1016｜PLAN028共享TUN真实Rust读者与认证/32 native分发接线（SOURCE候选）

## 已确认的上游事实

H1013 SOURCE `74b1fa101a7e912cebbc20bfcdc937683c0c185e`，Actions `41579974216` Linux两个真实netns、一份已构建的原Go TLS/Rust M4二进制 **PASS**：保护TLS发放并在OS读回 `10.66.0.154/32`，UDP往返5包且双方Stop；同编译的Game2/Game4同服务端443端口真实损坏单lane+兄弟交付通过。Rust非FEC Common `41579974321` PASS；H1014 `41580302912` Governance/Feature Catalog两job PASS。保存了源锁证据 `docs/evidence/M0/PLAN028-H1015-SOURCE74B1-AUTO-IP-RUST-M4-AND-GAME-20261103.json`。Win/WSL2 `41579974280` Game4 lane2 TLS bootstrap deadline **FAIL**；旧 PLAN020 revision3静态门禁/H998物理MTU/ARM64 Game4FEC失败一律保留。

## H1016 产品源码（不是另一个加密/recovery owner）

- `crates/wbd-engine/src/v4_embedded_go.rs`新增以原Go的真实 `os.File` TUN fd经Rust `BorrowedFd.try_clone_to_owned` 和既有 `ScopedTunSink` 建立的进程级单个读者，非测试替身。仅有一个process reader；`wbd_m0_embedded_go_shared_tun_open/bind/close`私有C ABI；服务端单TUN Stop须在所有子generation原Rust Stop后才完成。
- 主读取者每包只根据已经由真实Go保护TLS绑定的目标 `/32` 在HashMap中查目标。原内核 TUN IPv4报文通过**现存** `OriginalTunIngress::Shared` 有界队列送至目标generation，原Rust TX才拿真实M1 slab、走原Normal或Fixed/Auto封包和M4 raw。没有Go稳态包泵、AEAD复制、PN切换、新header/丢包重传框架。
- 重复同租约代际 A→B 只在**B真实Rust RX/TX workers起好后**发布覆盖旧路由并将旧generation的alive fence撤销；旧Stop必须凭精确generation及Arc地址比较删除路由，不能误删新的B；另一个账户/设备的不同IP路由无关联。原M1 TX封包前复核alive防止过期generation继续取源。已提供两设备加同IP接管/老Stop拒删的原生Rust纯单元测试。
- 单个目标满队列时有界backpressure并保留内核已经出队数据，不能静默掉包；一次只分配一个真实TUN读缓冲。当前实现包括`Vec`有界所有权拷贝和mutex保护HashMap，非性能/CPU优化证明；复杂弱网场景待用数据验证。
- `r0/go_overlay/internal/realityfront/bridge_v4_embedded_linux.go`新增共享TUN reader独立Stop与Rust handle的真实Go封装；`bridge_v4_linux_server_product.go`只有服务端受保护自动租约/32能绑定该reader，手动未认证/32拒绝；`v4productcli/linux.go`仅已有auto-lease选项创建/关闭共享reader，并禁止单peer回调改全局TUN MTU。原手动Normal/Fixed/Auto和Game旧模式不改默认读者。
- 原生双netns自动IP harness 强制 Rust shared reader真实停机聚合计数 `routed≥5`、readback 和TUN UDP app；相同构建原普通Normal、Game2/4和FEC short smoke作为回归，`.github/workflows/m0-plan012-combined-functional.yml`同时检查三个新增ABI符号及真实generation-fence单测。

## 严格资格边界

**当前为`IMPLEMENTED_NOT_TESTED`，不得提前声称原生共享reader PASS。** 新源码必须成功编译、内核观察到单reader路由及拆毁、真实TLS/UDP Stop。尤其**Go接入器当前仅允许一条逻辑设备**（唯一`V4LinuxServerProduct`），所以此提交只是 A→A+B→B 的内核基础，不是跨设备并发完成；后续必须真正扩Go TLS单端口接入、窗口并行真实用户B+C、独立Stop/MTU、更改Linux/Windows network event前完成七模式和Game4最高FEC。旧H998物理MTU FAIL不得重写。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"One real shared Rust TUN reader bound only to original-Go authenticated auto-/32 with per-generation O(1) destination routing into original Rust M1 owner; exact native test and Linux netns reader counter added, full concurrent Go admission not yet wired."}
```
