# PLAN028 H1537 — Linux 原生实测 300–350 Mbps 与 Windows 五 Wintun 实际首次路由阻断

已执行独立 [H1531 Linux Actions](https://github.com/lly8666/wbd-next/actions/runs/42788212678)，真 Go TLS443 + Rust/ISA-L、五种模式/五真实账户、双向 UDP/TCP，200ms 每个物理方向，600s；同一老原生产品 SOURCE `9b260553`，单独包装 `0a7d771d`，10秒 `tc -s -j` 真外层两方向合计数，六个 owned Stop。

- 0% 原 Job129734687736，ZIP13750603031：333.930 Mbps（目标300–350），真客户端/服务端认证 M4、五租户双向UDP/TCP、Stop 六进程和宿主资源硬门 **PASS_SCOPED**，Action SUCCESS。输入每方向60Mbps只是负载，实测外层333.930。
- 30% 原 Job129734688202，ZIP13749983094：303.027 Mbps（均值在带宽目标），六个原生Stop、其他所有账号和CPU guard均 PASS；但**Dave Game4 五次原始热lane READY，服务端仅三次真实 M4 READY**，故完整业务 **FAIL_SCOPED**。独立 [H1533 原始ZIP离线凭证](https://github.com/lly8666/wbd-next/actions/runs/42790451307) 表明缺口 lane3 port59341@09:14:55、lane4 port50881@09:17:04；服务端日志完整165149B且自09:08:55起，并非1.5MB日志裁剪或单测门槛误报。不得以“303Mbps达到区间”作完整产品 PASS；不重复跑0%或刷随机seed。
- Windows [Action42788212994](https://github.com/lly8666/wbd-next/actions/runs/42788212994) ZIP13751392741：父级真实 198.19.254.1 WSL源地址收据复用、本次无双重 Prepare，原200ms双向 netem清理、原host/guest地址和WAL清理均验证 PASS；Windows/Go+Rust、Linux对端与官方signed driver构建前置PASS。新第一异常 Windows app `bind(10.66.0.2)` WinError10049，但[H1536 真实五 client/server 日志](https://github.com/lly8666/wbd-next/actions/runs/42790915867) 更早显示 Alice/Carol/Dave/Erin `windowsclient: route is not owned; refuse to replace`，Bob原始Rust RX=0、Context deadline；五个客户端都未真正 Ready， **WINDOWS 五客户端 NOT_QUALIFIED**，不是仅延长app bind超时能解决。需原生Windows多 Wintun /32与同一共享服务端路由所有权正交隔离，不能跳过原已设计的第三方路由防护。既往H1387双客户端B同类未通过，不能声明产品已修复。
- 用户认可的旧 600秒 Linux H1520 0% 185.352 和30% 136.511 两场所有原始五客户端业务/M4/Stop均**PASS_SCOPED**；旧0%的历史100–150Mbps目标 **超标** 事实保留，旧30%该带宽目标 PASS；不得改写证据。
- Android/物理WAN NOT_RUN，PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","reason":"No production code change at this checkpoint; records source-locked actual native Linux two separate VM stress and Windows original Wintun route-ownership first fault without relaxing Go/Rust/WAL contracts.","ids":[]}
```
