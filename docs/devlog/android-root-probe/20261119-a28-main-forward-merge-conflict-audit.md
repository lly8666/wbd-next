# A28｜将 main 冻结主线并入 Android Root 实验分支：7个交叉文件冲突审计

- **授权与分支**：用户要求同步 main 的最新开发代码、功能、功能卡与所有开发历史档案；仅实验分支。冻结实验 `cd6207bab1eb624f8f5b51bdec06854fbee77076`，main `46a756df1114aecda8dc2d5d259a5cbb4c9a909f`，共同祖先 `0e57cab2d53e2c95962eb673050fa54695fd3665`；main 独有 266 commits，实验独有244。用第二父提交将 main 的全部祖先及历史纳入一条 merge，不 cherry-pick 某份孤立文件。
- **方法**：候选树以完整 main ROOT tree 为基准，只覆盖实验单边新增资产（Android Root app/native, Android-only Rust/Go/CI, Root功能卡和唯一计划、实验归档）与7处共享源码 conflict 的**祖先级 line diff3**。原 M0 决策、devlog、evidence、main 功能卡、registry/cursor、Windows/Linux/OpenWrt 源码与平台 workflows 全部保持 main HEAD 原版 blob。
- **真正共享路径冲突（7）**：`android/README.md`；`crates/wbd-engine/src/lib.rs`、`v4_embedded_go.rs`、`v4_owner_crypto.rs`；`r0/go_overlay/internal/realityfront/bridge_v4_embedded_linux.go`、`bridge_v4_linux_client_product.go`；`r0/go_overlay/internal/v4productcli/linux.go`。Rust 3 与 Linux embedded bridge 基本不同行；Linux client product main 新 padding 在原 Android 排除 M2 之前插入；原 Go linux.go 需要合流同插入点的 Linux Server 网卡自动IP 与 Android 根物理 Network 守卫以及服务端跨关联容量日志、实验原始 AF_PACKET SYN观察。禁用凭空吞并。
- **main 重要新能力/局限**：TLS 标准证书红线、允许8–32 ASCII route-key v2 本地 KDF+私有缓存（弱短Key熵仍弱；实验 APK 继续原64hex）、Linux服务端真实TLS decoy（未认证普通访客最多8，15–45秒关）、Linux NAT 自动接口IPv4、Rust owner 32 槽/Go Cold64槽（不代表真实32并发通过）、Linux authenticated Normal/FEC padding；main 历史 Windows/GUI、Linux 双 ISA 与跨平台、DNS、OpenWrt 继续以各SOURCE各平台收据为准。这里仅继承功能源码与 M0档案，不移植 Windows GUI 到 Android APK。
- **Android 保留门**：签名 ARM64 Root App，纯 Go/Rust 原数据面 Normal/off，真实物理 Network handle，源锁 32-byte hex route key + 标准TLS/账号认证，root私表服务器IPv4/32 throw +普通App IPv4 UID exact rollback，限枚举诊断 SAF 导出，不默认 x86/KSU/TAP 运行，真机与原 Linux 实际联机仍 NOT_RUN/NOT_PROVEN。
- **需CI实证**：合并 SOURCE 的 Rust 代码门、原 Go CLI/原 Linux server、Root Bionic Go/Rust签名 APK、纯 Java/脱敏门、功能目录治理；任何 build失败保留原始失败再最小修复，不用 fake mock 假PASS。当前只是完成三方源码整合，不能把候选 merge 预先称 PASS。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"全量合并主线新源码与历史功能档案进入 Android 实验分支；七个三方源码冲突保留 main 与独立 Root 合法实现，CI 后再更新资格。"}
```
