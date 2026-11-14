# PLAN029 H1820｜完整链接Windows V3 ABI后才允许复用/真机，不把ISO加速DLL冒充V3

- H1818 P2 [Action43573210008](https://github.com/lly8666/wbd-next/actions/runs/43573210008)已实际启动Windows原Go TLS认证，但 Windows native在Ready前以 `Failed to find wbd_m0_win_native_v3_start procedure in ... wbd_engine.dll` 失败；Linux server真实开启后owned Stop。H1819 P1 [Action43573356427](https://github.com/lly8666/wbd-next/actions/runs/43573356427) A腿在相同成品上真实50Mbps/25ms/0% 60s、约0.69839 GiB唯一交付，Windows RTT p99 47.0ms、Linux 54.209ms，owner Stop PASS；B腿同样缺V3导出而FAIL。不是抖动、容量或单测误判，绝不继续借这个DLL作为Direct资格。
- 已回查真实Rust源码：`crates/wbd-engine/src/v4_windows_native_runtime.rs` 的 `wbd_m0_win_native_v3_start` 只在 `#[cfg(feature="m0_v4_probe")]` 编译；H1814新P1 marker未设 job-wide `WBD_PLAN029_NATIVE_V3_TRIAL`，编出的release features仅 `m0_v4_embedded_go,fec2_product_record,native_fec_acceleration`，因此原ABI未导出；单纯哈希通过并不能证明某功能存在。
- 本H1820选择独立`[plan029-v3-real-p2-rebuild]`，**不用无导出旧缓存**：恢复现有Windows CI的原Go + Rust ISA-L + 显式m0_v4_probe，Linux Go/Rust同SOURCE一并构建一次；紧贴 `Copy-Item` 后、安装任何签名Wintun/NPF前由 Windows `ctypes.WinDLL` 实际加载DLL并 `getattr(...,"wbd_m0_win_native_v3_start")`，缺symbol直接FAIL。继续既有Rust owner单元门和真实签名Normal Direct/Tunnel/P2物理TCP 1MiB+小Tunnel UDP与owned Stop，不恢复高压旧028矩阵。
- 仅工作流/静态测试/cursor；未改正式产品DATA/ABI/Rust符号定义。等待H1820编译后的真实导出与网络结果，后续P1只能用这份“V3导出已验”SOURCE的产物，先校验hash/feature/diff。不虚构P1/P2整体绿。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix missing feature selection for actual V3 Rust DLL product build in targeted signed P2 run; add Windows-native symbol export fail gate before driver install; no product code change."}
```
