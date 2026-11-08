# PLAN028 H1439｜限定跨 OS 1800s 验收的 GitHub Runner 管理路径

Action [42517812264](https://github.com/lly8666/wbd-next/actions/runs/42517812264) 在 SOURCE `5a41a45` 完成 cheap/Go+Rust/ISA-L/真实签名 Npcap/Wintun/WSL2 预检，但原生第19步仍 `in_progress`、Job `failure`，下载原始 job 日志 `404 BlobNotFound`，无 1800s app、最终 owned Stop 和清理回执；对应范围 **NOT_QUALIFIED**，不是产品 FAIL/PASS。原 ARM64 eef2 两独立 1800s 保留 `PASS_SCOPED`，H1424 Windows+Linux 两账户 TLS/UDP/TCP/Stop 仍 `PASS_SCOPED`。两次同环节失联后不刷 seed，先区别长运行 Runner 断连与真实 app 故障。完整状态见 `docs/evidence/M0/PLAN028-H1439-WINDOWS-L3-SECOND-RUN-NO-FINAL-RECEIPT-20261109.json`。

本轮不改产品：复用已有 `m0_wl_gamefec_management_route.ps1` 已验证的 Runner.Worker/Listener **当前建立连接 /32** 按真实物理接口/下一跳 CAS 安装、读回、精确 owner 恢复，仅在 `[plan028-win-linux-co-client]` + `[plan028-win-linux-1800]` 同时出现时接入。独立 `crossos1800-management-route-lease.json` 防止与 Normal105/GameFEC 混淆；在真原始 app 前 Arm，原始 Stop 后 Restore。增加离线 workflow/权限边界静态回归，整个业务 1800s、TCP/UDP 和 Stop 门槛不降；若无活动 IPv4 Runner 管理对端则 fail closed 为夹具/环境阻断，不冒充产品问题。该变更是**诊断性最小对照**，不是已证根因修复，需真实触发/OS读回及业务收尾物证才判定。

```feature-impact
{"kind":"none","ids":[],"reason":"Only bounded GitHub Actions runner management /32 lease wiring for explicit PLAN028 native cross-OS 1800s test, no customer-facing product/config/protocol change."}
```
