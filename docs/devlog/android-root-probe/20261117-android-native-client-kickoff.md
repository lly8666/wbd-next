# 2026-11-17 Android Root 正式产品适配开工｜进度恢复与授权

## 来源与事实

用户明确授权由探针转换为 Android 原生 WBD 客户端，覆盖旧 `docs/prompts/ANDROID_TEMP_ROOT_PROBE.md` 中“仅探针/不开发完整客户端”禁令；不改M0 registry/cursor或 main 主线。2026-11-17读取GitHub：Android HEAD `1f77125bc175d3d9fd55c93f6c371e6b20dc7a16`，main `0e57cab2d53e2c95962eb673050fa54695fd3665`；共同祖先 `3b2c6e267d6b7047f334c450bcbc2c37bdbe4a19`，Android改动157个blob、main改动192个blob，无重叠路径。创建无force双亲merge `d5126fcd4cc7c848b62181ebddf8dadcb4225397`，Android历史完整保留，main未变；此节点之后应再读远端实时HEAD。

最近完成KSU Action [43986417528](https://github.com/lly8666/wbd-next/actions/runs/43986417528)，源码 `09a6a7e5f8aef5c3b38abb262655561ca89e5f9a`：真实App→KSU、私有网络DNS6/6、CN8503/4119合并、原生TUN/RAW/UID策略/NAT隔离均在原证据范围 PASS。[历史详情](20261117-android-cn-geosite-dns6-kernel-final.md)。另有用户提供的 Android16 ARM64 KSU 实机主诊断 JSON：10/10已执行项 PASS，涉及IPv4/IPv6 TUN、RAW、SO_MARK、策略18/18、UID10/10、合成NAT；手机截图的保存页显示geosite 8503和 `dns_udp_gate=SUPPORTED_IN_SCOPE`。截图没有逐条DNS case，未冒充同一真机六条独立校验。未经过真WBD服务器/系统DNS/生产主路由/真实热点USB、真蜂窝CLAT/切网和电池测试。

## 开工工程核查

真实产品共享Rust `crates/wbd-engine/src/v4_embedded_go.rs` 与 `crates/wbd-platform/src/linux_raw_carrier.rs`、`linux_tun_sink.rs` 的完整驱动路径受 `target_os=linux` + GNU/musl 编译限制；现有 `r0/go_overlay/internal/realityfront/bridge_v4_linux_client_product.go` 在 Linux/cgo feature 下做原Go标准TLS/认证→Rust owner。Go源码按 [assembly/manifest.json](../../r0/go_overlay/assembly/manifest.json) 从固定 `lly8666/wobuzhidao` 合成；不能简单取 `r0/go_overlay` 作为完整Go模块或拿诊断Rust当产品数据引擎。Android NDK/Bionic的 ABI/16KiB页和正式链路真实接通尚 NOT_RUN。

## 工作状态 / 唯一下步

A 产品装配与Normal/off实际连接 **IN_PROGRESS**：接下来做 Android source-locked Go donor + 共享Rust target preflight/编译产物，识别Bionic阻塞并最小共享接口抽取，继而实际Android16 KSU ↔ 同源Linux WBD server的标准TLS、认证、租约、Rust双向TCP/UDP/Stop。B统一DNS/路由/App选择，C生命周期/模式，D热点USB/PR皆 PLANNED；不以合成探针代替。后续完整包需记录冻结 SOURCE、Action、失败、未测和唯一下一步。

```feature-impact
{"kind":"added","ids":["android-root-native-client","android-temp-root-probe"],"reason":"用户授权从已完成范围内Root能力探针进入正式Android原生客户端适配；新增独立产品卡与现行施工方案/长期接续入口，保留旧探针历史与NOT_RUN边界。"}
```
