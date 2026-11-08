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
