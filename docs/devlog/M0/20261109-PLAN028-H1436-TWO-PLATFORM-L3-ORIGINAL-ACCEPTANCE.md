# PLAN028 H1436｜原生 ARM64 与 Win–Linux 两平台 L3 原始验收

2026-11-09，按用户要求先刷新 main 与运行中的两条原 Action，不按绿色推断业务 PASS、不盲目再发 30min seed。

## ARM64：实证两场 PASS_SCOPED

[原 Action42505975134](https://github.com/lly8666/wbd-next/actions/runs/42505975134) source `eef2a81383fec3e10a78d9e2dda29af799a11d90` Go/Rust/build job及 baseline/heterogeneous 两独立原生 runner job **三者 SUCCESS**。原 ZIP #13628054467（SHA256 `64d655e63c...`）、#13628472837（`183dad6370...`）分别36文件 CRC 全 PASS。原 pinned ISA-L 源 `c387163f...`、native AArch64/ Go1.23.12/Rust1.85.1、一套二进制 SHA 所有报告一致。

两场各 **1800 真业务秒**；五个原 Go TLS443/Rust M4 受认证租约，Normal/FEC Auto/Game2/Game4/FEC Fixed，原生跨代 Rotate/Old Stop 和最终严格 owned Stop 全 PASS；原 10ms app 活跃期间最大 no-RX 50ms / 120ms，配置 alert **0**，每租约待发 overflow 0。每场十条测试专属永久真实 veth neighbour 安装并终态读回 PERMANENT，排除网络损伤期间 ARP 变量混杂。hetero Erin 真实 tc DATA 丢包上/下 30.026% / 30.006%，不是口头配置。真实 Game4 客户端 `native_linked=1 selected=prefer-native`，baseline TX616047/RX decode5518，hetero TX904315/RX decode152541；服务端 TX615620/903621、decode5463/153410。hetero Erin 一次失败 cold candidate 仍原样记录，之后成功的16代、Stop全证实。不抹掉该诊断，也不把非物理 WAN 说成物理机资格。

## Windows＋独立 Linux：L3 暂未取得资格

[原 Action42508261361](https://github.com/lly8666/wbd-next/actions/runs/42508261361) source `d6aeb6462de5a249399b9cfbe15701df287f07d9`：便宜预检、Windows Go编译、Windows Rust单测、Linux Rust单测、同源原 Go TLS/Rust Linux 构建、Windows static ISA-L＋Rust release DLL、真实签名 Npcap/Wintun安装、WSL2 Linux kernel boot 全 SUCCESS。Windows native 第19步 `Launch actual WSL2 Linux and direct full public two-OS product` 进入 `in_progress`，但最终整个 native job `failure`；这一步没有形成完成记录，其后上传工件与清理步骤均 PENDING，期望长测报告没有上传。GitHub 这个 job 的 logs API 返回 **404 BlobNotFound**，其他 preflight job 可读取。

所以正式分类 `NOT_QUALIFIED_NATIVE_STAGE_NO_ORIGINAL_1800S_AND_STOP_RECEIPT`，不是 Windows 真功能 PASS，也没有把未得到产品故障证据的外部/CI未知错误强行认定协议 FAIL。已完成的 H1424 Windows A 单签名 Npcap/Wintun+独立 Linux B 同一443，两用户双向真 UDP/TCP、A owned Stop 后 B 继续、B/server Stop和 OS清理 **PASS_SCOPED L1** 仍成立。后续先缩小 runner/network 活性边界与保全原回执，再唯一精准恢复原生 Windows L3；不重复ARM长测，不扩协议。

完整逐项原始证据、SHA、业务计数、丢包/ISA-L读回与平台限制见 `docs/evidence/M0/PLAN028-H1436-ARM64-2X1800-PASS-WINDOWS-LINUX-L3-NOT-QUALIFIED-20261109.json`。PLAN028 **IN_PROGRESS**；旧 H998 同socket HOT MTU FAIL、Android/用户物理机 NOT_RUN、029/030不得启动。

```feature-impact
{"kind":"none","ids":[],"reason":"Native long-test acceptance and truthful source-indexed evidence only; no product protocol/feature change."}
```
