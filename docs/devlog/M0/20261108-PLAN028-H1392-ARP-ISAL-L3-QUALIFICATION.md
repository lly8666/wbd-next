# PLAN028 H1392｜1800s L3 ARP/DATA 分账及原生 ISA-L 验收

2026-11-08，main 自 checkpoint c42c、增量 645a 接续。**功能冻结仍为 IN_PROGRESS**；只修测试夹具/真实 native 构建资质，不改 Go/Rust 产品数据面/协议。

- [H1389 原两条 1800s](https://github.com/lly8666/wbd-next/actions/runs/42466954711)：真实 ARM64 Go TLS443/Rust M4 五客户端、所有 authenticated rotation/Stop 合格；健康基线 0 警报 PASS_SCOPED，异构 Erin 30%/125ms 两方向实际活跃发送无收件分别 3310/3320ms，**性能 FAIL**。[H1390](https://github.com/lly8666/wbd-next/actions/runs/42472269266) 原原始数据离线验证不改变结论。
- 已验短测 H1312 ARM64、H1313 x86 通过真实六 namespace 的 10 条原始双方 veth 邻居项 PERMANENT，让 netem 30% 损坏 DATA 而不同时损伤 ARP；当前脚本却禁止长测开此开关。H1392 只放开显式长测，真实 MAC 读回安装/Stop 后共 10 条并保留 qdisc 损伤原始计数；旧动态 ARP 失败原样保留且不追认其全部成因为 ARP。
- 原 H1389 编译 `wbd-engine` 的 features 没有 `native_fec_acceleration`，不能计为 ISA-L 资格。新 native ARM64 构建从 pinned Intel ISA-L v2.31.1 SOURCE `c387163fcbca62701d646149564c550c78a4f985` 构建静态档，SHA256/ELF/原 Go 组件记录 manifest，Rust feature 及单测保持一致，原生 Game4 生产 Stop 读回要有 `native_linked=1`、`selected=prefer-native`、`tx_native_quanta>0`；合法短块 scalar 和 FEC Off 零 quanta 不算掉加速。构建链接≠运行时证明。
- 用户最新口径是 Windows 单机单 VPN 实例、多设备共用 server。H1387 同机第二 Wintun 原所有权 FAIL 保留但不为它新增产品例外；优先 Windows 真 Wintun + 独立 Linux 认证客户端和 Stop 隔离。已有 H1388 Windows 同 NIC/IP MTU1500→1280 真 TLS/UDP/TCP/Stop PASS_SCOPED 复用。H998 原 socket hot PMTU FAIL 不能改写。
- 本提交是修正候选，**新 H1392 测试/应用业务状态在 Action 实际回执前为 NOT_RUN**；旧 H1389 问题还未关闭。如排除 L2 后仍有稳定容量内数秒停顿，先定位实际 qdisc→raw rx→AEAD/FEC/TUN→业务，勿刷随机 seed 或放宽硬门。

```feature-impact
{"kind":"none","ids":[],"reason":"Diagnostic native test topology and ISA-L artifact qualification only; no product/feature/config/wire changed."}
```

## H1392 首次 Action 的离线预检错误

源 `71fa9c3d` 推送后 [Action 42475181912](https://github.com/lly8666/wbd-next/actions/runs/42475181912) 直接在 workflow 解析阶段 FAIL，jobs=[]，**没有执行构建或网络，产品 NOT_RUN**。原因是生成 YAML 时文本替换把正则 `ec_encode_data$` 后面的单引号错误识别成替换特殊序列，尾部被复制；本次恢复唯一有效 workflow 及完整 `nm`、Cargo Native feature 指令，业务参数、原错误物证不变。属于 `HARNESS_OR_CI_FAILURE`，不能当 ISA-L 产品失败。同步触发的其它原有 path-filter 工作流只记独立结果，不重复 dispatch。

## cursor SOURCE 一致性修正

[治理 Action 42475419694](https://github.com/lly8666/wbd-next/actions/runs/42475419694) 和 [maintenance 42475419683](https://github.com/lly8666/wbd-next/actions/runs/42475419683) 于 `4444328` 真实失败，因为当批 cursor 将 `last_tested_source` 误改为 `096a`，却保留了全部 `6c5` 来源的 `evidence_refs`，仓库守卫报告 `evidence is for a different SOURCE`。这不涉及业务或测试结果。保留两组来源独立、恢复该字段为原来 `6c5fd909...`，H1389 `096a` 放在既有独立证据，H1392 新 SOURCE 仍等待原始 Action 回执。不要为元数据不一致重跑网络。

## H1393 跨目标原生 ISA-L release 链接资格（构建≠运行时）

在现行 `.github/workflows/m0-wl-public-normal-full.yml` 读取到 Windows 正式 DLL 的 `$features='m0_v4_embedded_go,fec2_product_record'`、Linux 正式 Rust build 的 features `m0_v4_probe,m0_v4_embedded_go,m0_fec2_owner_probe,fec2_product_record`，均**没有** `native_fec_acceleration`；仅设置环境 `WBD_GAME_FEC_BACKEND=native` 不能改变编译期缺失，属于用户指出的默认硬件加速掉线风险。不能擅自直接让整个 Windows 多模式/双 Wintun 生产 CI 跑大矩阵。

新增一条独立 H1393 build-only 工作流：原生 Linux x86 与 Windows2022 x64 MSVC 分别用官方固定 SHA `c387163fcbca62701d646149564c550c78a4f985` 的静态 ISA-L，实际 Rust wrapper C encode、`wbd-engine` release `native_fec_acceleration` 严格链接，写 target/features/SOURCE/静态档及 DLL/ELF SHA256。**不跑 Npcap/Wintun/Go TLS/任何真实数据面**，这轮只能判 build/link/scalar-fallback 装配资格，不能由此宣布所有 mode、所有操作系统的硬件加速可默认启用。等结果后才最小接入现行 release、再对真实非零 FEC/native runtime quanta 和两端业务做验收；原 ARM64 H1392 长测仍按独立冻结 SOURCE 跑。

## H1394 实际 Windows/Linux 产品装配默认启用 ISA-L（单 Windows Game4FEC 限定场景）

H1393 [原生构建 Action 42476161525](https://github.com/lly8666/wbd-next/actions/runs/42476161525) 两 job 均 SUCCESS。下述真实 native manifest 已从 artifact 原 ZIP CRC 验证：源 `b7c99ec3...`；x86 Linux 静态库 SHA256 `033b22b9144c25036b0cb0267c273d7adf6e062241f00baa9227546c7972dc6d`、release ELF `ef63fa8cf08667a7b1b1961c1804a7b11aa0fe715a65b9eee83d66580f4ccad6`；Win x86_64 MSVC 静态库 `f625d6b927319c81970ca31346ab7346ad32921d4df741e20f6360473266f7bd`、release DLL `a6a2b5773404c38ca7c15310ed8faac0d5e5c35b6bc60a5d80cc6983c7b3a546`。两者真实 pinned Intel ISA-L C encode 测试+实际 Rust 动态库 native feature PASS，**并非原 Go TLS、Npcap 或 FEC 业务运行证明**。

由于现行多 OS 原始产品公开组装仍没有该编译 feature，本轮在唯一 `m0-wl-public-normal-full.yml` 的 Linux 原始 GoTLS/Rust server/client release 和 Windows **单原生客户端** release 加入固定官方源码+静态档构建及 `native_fec_acceleration`，manifest 记录官方 SHA、native feature、静态档 SHA256、二进制 SHA256；缺少档则构建 FAIL，不伪装 scalar 为硬件加速。利用既有明确 `[plan028-win-physical-game4fec]` 限定单 Game4+FEC Windows 原生场景，不启动二 Windows 客户端、不运行七模式矩阵；真正产品/Stop/native FEC quanta 按当前 Action 原始证据另行判定，先写 **NOT_RUN**，不可因为上方 build PASS 宣告产品默认各模式全面验收。原 H1387 同机第二实例 WAL/route FAIL 保留，跨设备 Windows+Linux 客户端仍须单列验证。
