# PLAN029 H2064｜首次真实两代 GUI 与 TTL 失败的共同收敛和定向夹具修正

第二轮 3 个独立 Action 全部通过 source-locked Windows/WSL2/GUI schema/真实原产品 Connect1：
- GUI [44014381270](https://github.com/lly8666/wbd-next/actions/runs/44014381270) artifact14298411784：第一代原 TLS/WinForms/Wintun、1460外层/1389内层、owned WAL Stop 真 PASS；`PLAN029_H2061_NORMAL_GUI_FIRST_DISCONNECT_WAL_ABSENT_PASS` 后**未出现第二代 Go/TLS 日志**，12s后夹具判为早退，不是第二代网络业务失败证明。
- 域名 [44014385888](https://github.com/lly8666/wbd-next/actions/runs/44014385888) artifact14298251666：第一代 Linux 物理 UDP TC1→同 DNS endpoint TCP53 `id=e752`、选定域名、原 TLS/OS/Stop PASS；同样未见二代启动，故 `reconnect=NOT_RUN`。
- TTL [44014389751](https://github.com/lly8666/wbd-next/actions/runs/44014389751) artifact14297649170：首个真实 CN app QNAME `www.cn.example` 回 FakeIP `198.18.0.1`；2.8s TTL 过期后第二查询收到 negative/empty，完整重启阶段未测成，`FAIL` 保留。不可假称这是产品缓存 bug，首先分开原 physical ID、物理回执和本地合成结果。

原被测 WinForms `MainForm.DisconnectAsync` 设置“未连接”**早于** `RunAsync` 的 finally 清忙状态/重新 enable 按钮。旧夹具只等 `!Active` 和“未连接”，立刻 `PerformClick` 可能打在禁用状态而被吞。新夹具必须同时等可见用户按钮 `Enabled`，`Click` 之前也校验且打印点击标记；不加入任意 sleep，也不绕过真实 GUI/Go。

Rust `DnsPending::begin` 以独立 upstream ID 重写真实物理 DNS 包；新 TTL 物理 guest helper错误假设 upstream ID 等于 Windows app 的原 DNS id，而且新 Go/Rust generation 可从 1 重置。改为源UDP端口＋物理上游ID作为真正查询单位；三个原 app txid独立校验；保存适度脱敏的物理DNS guest log、neg RCODE/answer 计数，若下轮有真实其它bug能定位首个边界。不触碰产品 Rust TCP/UDP/FakeIP、协议或旧 owned Stop。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback","dns-split-ipv6","client-domain-bootstrap"],"reason":"H2064 first original GUI generation/owned Stop real PASS, second click and TTL phase2 first failures retained; improve fixture first-error observability only"}
```
