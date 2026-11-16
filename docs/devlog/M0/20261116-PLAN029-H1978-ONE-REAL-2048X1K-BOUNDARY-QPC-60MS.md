# PLAN029 H1978｜只复核大差距的原生Wintun/WinSock边界，不重测极端工况

- 真实异常为前次 SOURCE `bd611192c397220d467a8330defce4e0d494ac04`、[Action43808776053](https://github.com/lly8666/wbd-next/actions/runs/43808776053) 的 **5×61–63ms Direct原TCP请求卡顿**，四次真实重复TCP序列；原Action QPC严格业务关联FAIL，不许误报PASS；Linux/Windows 2048条1KiB+32预热的真实SHA/FIN和双Stop PASS。
- H1977纯源码SOURCE `c66d37a4f3dafa757150a3562699fd05a1ad745d`，廉价 [Action43815755069](https://github.com/lly8666/wbd-next/actions/runs/43815755069) 的 Python **6项H1977分析器回归+合约**、Windows Rust、Linux Rust和Windows Go正式编译已 PASS；[Governance43815754975](https://github.com/lly8666/wbd-next/actions/runs/43815754975) 两项PASS。先收本SOURCE的original Linux peer persona build才独立发此签名网络测试。
- 本H1978仅加原生工作流**顶部注释**使 push 命中原 `on.push.paths`，提交信息明示四个源锁scene标记：`[plan029-v3-real-p2-rebuild]`、`[plan029-v3-real-p2-steady-qpc]`、`[plan029-v3-real-p2-post-ingress-flush]`（复现上次只签名的8条同轮交付）、`[plan029-v3-real-p2-boundary-qpc]`。其他产物/Rust/Go/工具的字节都来自已检过的H1977源码。无4MiB、ABBA、preconnect、128连接、极端DNS/CDN；默认普通产品**两项signed行为均OFF**。
- Windows原Wintun的1条已建连接、物理socket基线、原WSL2 Linux TCP46119各2048×1024B，先各32热身；签名诊断按原source port→proxy port→SEQ、本机Win32 QPC核对TX channel和RX `WintunSendPacket`调用/返回及原WinSock FD_READ。Stop后`plan029-h1977-boundary-qpc.json`侧证**在严格H1966检验之前保存**，故即便有真正TCP重传导致原Action继续FAIL，仍保留60ms发生在哪一段的真实证据；不因为诊断侧证绕过原FAIL。所有数值从原artifact而非想象。

完整PLAN029仍IN_PROGRESS，尤其普通产品后发同轮交付未获性能资格；用户明确不要求同CDN真实IP极端反例。

```feature-impact
{"kind":"none","ids":[],"reason":"Dispatch only one source-locked ordinary Win2025/WSL2 2048x1KiB TX-mailbox/RX-Wintun/WinSock-FD_READ QPC diagnostic after H1977 pure CI passes; change only native workflow comment and M0 task note, no product modification or acceptance promotion."}
```
