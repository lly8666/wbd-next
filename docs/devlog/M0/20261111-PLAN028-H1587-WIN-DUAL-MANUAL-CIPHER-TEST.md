# M0 PLAN028 H1587｜复用真实双 Windows 签名驱动，验证独立手动IPv4与AES-128/ChaCha混合（2026-11-11）

**本记录创建时 NOT_RUN，PLAN028 IN_PROGRESS。**与独立 Action `43000134310` 的 Windows自动IPv4/AES256＋4Linux 150s H1586不同，本场在另一干净Windows2025 Action VM复用成熟的 `tools/m0_plan028_h1382_windows_two_original_tls_product.py`、原始Linux共享TLS443/Rust TUN、两个真实Wintun及已存在的 A退出/B继续原生资源硬门，不另造协议/数据面或OS控制器。

现有历史双Windows H1382支持各自账号、静态 `10.66.0.2/32` 和 `10.66.0.3/32`、两个不同安装ID/别名/WAL、真实原始Go证书TLS、Rust M4、双向Windows kernel UDP/TCP，以及先 Stop A 后B的真实UDP/TCP持续、终态双WAL/共享Linux Rust TUN Stop。本轮 **仅添加新的显式测试配置**：
- A 原生Windows client `--record-cipher aes-128-gcm`、手动 `10.66.0.2/32`；
- B 原生Windows client `--record-cipher chacha20-poly1305`、手动 `10.66.0.3/32`；
- 双端同一真正原始Linux共享Rust M4服务端，服务端受保护逐client策略独立运行 `cipher=2` 与 `cipher=1`。Windows每个原始Go保护TLS确认后的 `WBD_WINDOWS_AUTHENTICATED_NETWORK_SELECTION` 必须跟Rust `ColdSnapshot().Cipher()` 及配置手动/32匹配；不接受静默降级、复用另一个client密文或只凭参数字符串。
- 仍需实际本地 Windows OS Wintun独立InterfaceGuid/Index、首次双向UDP/TCP以及关闭A后B的业务、两WAL/服务端Rust TUN Stop。原 H1382真实压力门全部保留，本轮短场不写成L2 150s或600s/1800s长测。

使用既有 M0 native workflow 的原有 `[plan028-win-dual-original]` 入口，同时增加唯一 `[plan028-h1587-win-dual-manual-aes128]` marker 只用于差异配置、独立只读报告检查和廉价源级test；该 Action 只运行一个真实双 Windows 场景。真实运行仅认原始 `h1382-dual-report.json` 的精确SOURCE、两个Windows protected cipher读回、真实Linux服务端双cipher、真实UDP/TCP、A/B owner+server Stop和真实VM报表。该测试主要区分 **Windows AES-128 产品接线** 与 H1586 的 **AutoLease/AES-256**；不涉及同账号跨终端的已验证声明。随后单独对同账号多安装做最小真实验证，不偷换既有账号隔离。

**本记录不是PASS**。H1582 auto AES256 SOURCE3f82真实TLS和cipher3已验证但没有发送目标为自动/32的冷反向内核UDP；H1584/H1585/H1586已补测试侧真实发送者，结果仍在独立真实 Action；H1583 30pct manual ChaCha受保护TLS完成但原夹具同样漏冷反向，纠正后另跑，不因这场成功而推断30pct通过。保留所有旧FAIL。

```feature-impact
{"kind":"none","ids":[],"reason":"H1587 only configures a distinct existing signed Windows dual-original per-client AES128/ChaCha manual-IP acceptance scene and exact-source report checks, without changing product default, GUI, crypto or Rust data plane."}
```
