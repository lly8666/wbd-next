# A2 第二批｜原 Go 认证代际接入 Bionic Network / RAW / TUN FD

基线：实验分支 `1ccc56e4ff9437d694234fd64ff860e1cc997a04`；main `fb24fe784d960e3e8bf4ca63cc2a22332247e1dd`。本提交仅作用 `experiment/android-temp-root-probe`，不更改 main、M0 registry/cursor；无远端工作树，本次仅审阅远端已提交内容。

- 保留原 `r0/go_overlay/assembly` + pinned Go donor `a7a82db31fe736ffedee330795a3234d358f1984`；沿原 `V4LinuxClientProduct.ConnectAuthenticatedPeer` 标准 TLS → 验证/Detach → 原 Rust `prepare/stage/commit`，在 RAW attach 之前插入 Android-only 冷 `Network`/ifindex/MTU 绑定，接口 MTU由 `net.InterfaceByName` 读回比对，缺失值拒绝。Linux 侧独立文件保留原内核接口，不读取 Android Network 值。
- 同一个 `v4_embedded_go.rs` 的认证 Entry 增加 Android-only 的物理 scope、真实 Bionic tuple-filtered RAW RX、绑定 RAW TX、独立复制持有的验证 TUN FD。导出原 Go 调用的 `attach_raw_rx_on_interface`/`attach_tun`，以及 Android 专属冷 scope setter；实际 RAW FD 在原 TLS 后绑定，未建立替代认证/协议/PN。两个 RAW 打开任何一个失败就全部撤销，禁止不带 Android Network 的发送。
- Android 原 `stop` 通过同一共享 Rust `ProtectedScopedOwner` 将尚未发布给 M4 worker 的这些 owned FD 停用、去引用并关闭；没有 join 真实工作线程，不能标为完整 owned worker Stop。继续保持缺失 `loop_start` 等 M4 原符号的真实 Go 链接 FAIL，不能添加空壳 ABI。
- 原 A1 Action 的一个构建来源、双ABI Rust+Go 源锁不变；扩展真实 Rust 符号导出门与 manifest，使 `Rust COLD + ANDROID OWNED FD ATTACH` 和 `REAL WBD M4 WORKER` 分明，不将 stage 编译/链接等同真机权限、系统 socket 可用或业务 PASS。

此提交执行前测试状态 **NOT_RUN**；之后须以同一 SOURCE Actions 完成实际记录。Android16 KSU ↔ 同源 Linux server 标准 TLS/认证/租约、正常业务双向TCP+UDP、完整 M4/Stop、ARM64 装载/16KiB真机及加速仍 **NOT_RUN**，无设备部署授权。

**唯一下一步**：把这组同一 Entry 的 Bionic RAW/TUN 真实 FD 经原 Rust M1/M3 PN/AEAD/MTU/fair worker 收发循环消费并可同步 join，解决原 Go 全链接（而非新建 Android 逐包引擎），再进入 A3 真实同源服务器测试。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"原Go TLS/Detach冷控制加入仅Android物理Network scope，原共享Rust认证Entry实际收养四元组 RAW RX/TX及TUN FD，NDK双ABI源锁符号校验；M4真实worker仍NOT_RUN。"}
```
