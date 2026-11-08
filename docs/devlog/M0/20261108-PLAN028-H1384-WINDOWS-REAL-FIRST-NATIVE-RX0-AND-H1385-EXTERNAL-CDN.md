# PLAN028 H1384 / H1385 原生 Windows 原始收发与外部下载分账

2026-11-08。严格按真实产品受保护 TLS、原 Rust M4 收发、原 Windows 签名 Wintun 与停止证据裁决；若 A 实际 RX=0 且未 Ready，这是本场 **FAIL**，不同于测试报告器红灯；若签名驱动下载被外部 CDN 504 阻止，这是 **NOT_RUN**，不宣称本轮产品成功或失败。

## H1384｜真正 Windows 双认证原产品 A 阶段失败

- [原 Action 42464557691 attempt 3](https://github.com/lly8666/wbd-next/actions/runs/42464557691)：原 Windows2025 签名 Npcap/Wintun / Go / Rust M4 和 WSL2 服务器真实启动，服务端已看到 Alice 原 `V4_PUBLIC_MULTI_SESSION_READY`、`authenticated_TLS=1`, `Rust_M4=1`，服务器原 Rust TUN 收到48（UDP43）。
- 然而原 Windows A `WBD_WINDOWS_CLIENT_READY` **没有出现**，真原 Rust first+reverse 在 deadline 前 **TXCopied48 / RXDelivered0 / Rejected18 / WorkerError0**；原 Windows A 真实原 WAS Stop/WAL cleanup 完成。B 从未创建，因此双 Windows 同时认证/双真实 Win32 UDP/TCP / A Stop B继续统统 **NOT_QUALIFIED**。原 Action FAIL **必须保留**。
- 原 `h1382-app-A.log` 显示未配置完整产品路由前 `WinError 10051` 后测试 Windows UDP 应用退出，Linux `h1382-echo-linux.py` 仅被动 echo，从原 server TX 链 `staged_udp=0` 证实**无真实反向应用数据**。这是该源试验真实 first/reverse 未满足，不能伪造路由、M4 RX 或 Ready。原19文件 ZIP SHA256 `31a5e70a9be7b35318228f4643618d1301050220dc98ef3a82099353f85f4785`，CRC全部PASS，Artifact 13611722358。
- H1387 [新 Action42466552995](https://github.com/lly8666/wbd-next/actions/runs/42466552995) 只修**测试-owned**真 Linux kernel reverse UDP 双向流和 Windows 应用真实 socket route-not-ready 的临时处理：Linux 在客户端原进程启动后通过内核 TUN 主动发 UDP，Windows app bind 真实端口45901且不再因初始化时无路由永久退出；不能制造假 Ready；原 Go TLS/ Rust/签名驱动产品字节未修改。新运行自行验收，不预判 PASS。
- 官方证据：docs/evidence/M0/PLAN028-H1384-SOURCE4BF-WINDOWS-ORIGINAL-DUAL-A-REAL-NATIVE-REVERSE-RX0-FAIL-20261108.json

## H1385｜外部 Npcap 包 504 无法跑产品

- [Action42464619647](https://github.com/lly8666/wbd-next/actions/runs/42464619647) 三个 attempts，Windows Go/ Rust/ Linux Go/Rust 编译检查都成功，但安装真实签名 Npcap 前从 GitHub user-attachments 下载**固定 hash 源**得到 HTTP504，真实物理 MTU 1500→1280未发生，因此本源 **NOT_RUN**。不能把外部错误算作真实业务 fail，亦不能拿旧 H1364 不同源码的 PASS 凭空盖章。
- 新 H1388 [Action42466674474](https://github.com/lly8666/wbd-next/actions/runs/42466674474) 有界下载重试（最多五次），**原签名、官方 ZIP 与 SHA256 固定校验完全不变**；同样只有实际 NIC OS MTU读回、原 TLS/Rust新代、两端 UDP/TCP、Stop 满足才能 PASS。
- 官方证据：docs/evidence/M0/PLAN028-H1385-SOURCE553-WINDOWS-MTU-NATIVE-EXTERNAL-SIGNED-DRIVER-CDN-NOTRUN-20261108.json

## 并行已过门与未过门

- ARM64 原在线五客户端在跑180秒期间真网卡 MTU1500→1280、同源 IP 新受保护 TLS 和 Rust M4 代恢复 Action42465059734 SUCCESS，源8fd已另归档；不覆盖 H998 历史**同 socket hot**老 FAIL。
- 两条 ARM64 1800秒五客户端原 L3 [H1389 Action42466954711](https://github.com/lly8666/wbd-next/actions/runs/42466954711) 分独立baseline/heterogeneous 实景进行中；未有结果不得提前判定。PLAN028 仍 **IN_PROGRESS**。

```feature-impact
{"kind":"none","ids":[],"reason":"Source-specific H1384 true original signed Windows A Rust first+reverse RX0 native failure and H1385 external signed-driver CDN504 NOT_RUN archived separately; H1387/H1388 are test-owned fixture/delivery retries only, no product or feature-card changes and no premature capability promotion."}
```
