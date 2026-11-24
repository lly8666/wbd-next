# Android16 pre-Apr DirtyFrag：真实 guest 被 HVF 阻断，源码锁定收口（2026-11-16）

**唯一分支** `experiment/android-temp-root-probe`。最后测试 SOURCE `f43257dce625cb9504142eafa491659013857f9d`。**镜像文件实证通过；guest 没启动，DirtyFrag 没运行，root 与 WBD post-root 均 NOT_RUN。** 旧 KSU/adb-root 结果维持原 SOURCE，不替代漏洞 root。

## 镜像真实性

2025-12-02 的 [SDK 目录历史快照](https://github.com/eagletmt/android-repository-history/blob/7c23968450618e94727e190d3a2ad3cf8f24adf7/repository/sys-img/google_apis_playstore/sys-img2-1.xml) 已列 Android16/API36 Google Play ARM64 `arm64-v8a-36_r07.zip`，早于用户限定的 2026-04-01。Action 实际下载并核对 **1,886,527,965 字节**、SHA1 `5b91ef80a5eb60d7b7167528db259c2a12d20e9c`，计算 SHA256 `ddb0feff5c23db9f42ceabd28f6542e8ffec639abf818bf6831a2658e6cf7905`。`source.properties` 是 ABI arm64-v8a、API36、Google Play、Revision7。**内核6+、固件安全补丁及 guest 原始无root仍未读到**。

## Action 与失败分类（不改写）

- [43857158313](https://github.com/lly8666/wbd-next/actions/runs/43857158313) SOURCE `f0b835c7`：Ubuntu aarch64 无 `/dev/kvm`，ENV_BLOCKED。
- [43857610954](https://github.com/lly8666/wbd-next/actions/runs/43857610954) SOURCE `8342f575`：macOS 脚本误选旧 Intel emulator，已修复。
- [43858595528](https://github.com/lly8666/wbd-next/actions/runs/43858595528) SOURCE `640fc920`：当前 macOS ARM64 SDK emulator 的 **host** `-accel-check`=0，Hypervisor.Framework 15.8；这不是 guest boot PASS。
- [43859987790](https://github.com/lly8666/wbd-next/actions/runs/43859987790) SOURCE `22211f41`：ZIP 多嵌套一层 ABI 目录，夹具错误已修复。
- [43860416567](https://github.com/lly8666/wbd-next/actions/runs/43860416567) SOURCE `32f86c09`：`avdmanager` 缺输入 `no`，夹具错误已修复，镜像 SHA 验证通过。
- **[43860868119](https://github.com/lly8666/wbd-next/actions/runs/43860868119)** SOURCE `f43257dce625cb9504142eafa491659013857f9d`：完成 AVD 注册，真正启动 QEMU ARM64 时 `HVF error: HV_UNSUPPORTED`、`failed to initialize HVF: Invalid argument`，**ENV_BLOCKED**。Job `133277022985`、artifact `14222664457`，ZIP SHA256 `88ee8a4f78556c2a294e94d878328b2d219ee38ce8c829e00dcb3e4235db0492`（已下载独立验算）。`guest_booted=false`、`dirtyfrag_executed=false`、`post_root_wbd=NOT_RUN`；emulator 正常退出。**Action SUCCESS 仅代表证据上报成功**。

## 后续可执行门槛

1. 用**真正有 ARM64 guest 虚拟化能力的裸机**：Apple Silicon Mac + 可实际 boot guest 的 HVF，或物理 Linux aarch64 + `/dev/kvm` 和可核验的 ARM64 Android emulator。不能用 hosted runner 的 `-accel-check` 代替 QEMU 实际启动；不再重试此 GitHub-hosted 组合。
2. 原 ZIP 严格 SHA 锁定后，在**真实 guest**读 Android release/API36、security patch <2026-04、`uname -r` Linux6+、arm64 ABI、原始 UID/SELinux、`ro.debuggable=0`，证实 `adb root` 被拒；否则按 `ENV_BLOCKED/INVALID_BASELINE` 停止。核对 XFRM/IPsec、GKI KMI、vendor insmod/文件标签；如果 patched 或 helper 缺失，不伪造漏洞 PASS。
3. 如确实满足条件，下载 SHA 固定的 [DirtyFrag v1.10](https://github.com/mitschud/DirtyFrag/releases/tag/v1.10) 与含 `libksud.so` 的 [KernelSU Manager](https://github.com/tiann/KernelSU/releases/tag/v3.3.1)，普通 App 显式执行一次 bounded exploit。用户仅授权此隔离测试中 SELinux 临时 Permissive；记录前中后状态及 reboot 后恢复。只有真正 App→su 子进程 UID0/cap/SELinux 和内核受控操作实证才算 Root PASS。无 boot/system 永久改动，不连接真机。
4. 真 root 成功后再用原 SHA 锁定 ARM64 Rust 探针：默认 inspect、显式 owned exercise，验证 TUN 真读写、raw、netd/路由、DNS、IPv6、权限与正常/异常回收。**热点/USB 真实下游、eBPF offload、蜂窝切网与功耗仍是物理真机 NOT_RUN**。

**结论：** 找到日期符合且实物校验过的原厂 Android16 ARM64 模拟镜像，但 GitHub-hosted 的真实虚拟机能力已被日志否定。实际 DirtyFrag 提权与在该路径下 WBD 可行性尚无实测证据；本包按环境受阻收口。

[机器可读证据](20261116-dirtyfrag-preapril-matrix.json)

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Source-locked old Android16 ARM64 archive/hash PASS, actual QEMU HV_UNSUPPORTED environment block, DirtyFrag and WBD post-root NOT_RUN; preserve old results."}
```
