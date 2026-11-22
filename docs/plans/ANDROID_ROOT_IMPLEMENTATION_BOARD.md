# Android Root 原产品功能施工台账（B30｜源码与设备分层）

- **唯一工作分支**：`experiment/android-temp-root-probe`，对照基线 `f115ab1840f1c50eb1922f9c34b67267ca1fd770`，Draft PR #36。主线 `main` 不写。
- **证据**：[B29b Android Dual64 #44967461025](https://github.com/lly8666/wbd-next/actions/runs/44967461025) 为本SOURCE 11 SUCCESS/4 SKIPPED；[Governance #44967461013](https://github.com/lly8666/wbd-next/actions/runs/44967461013) SUCCESS。Android真实应用E2E/性能依旧未验。
- **口径**：`WIRED` 源码确实连入生产调用链；`HOST_PASS` 同SOURCE已有Host/ARM64编译资格；`PHONE_PARTIAL` 旧真实API36片段凭据；`NOT_RUN` 手机/真实双端业务未验；`MISSING` 确认无生产路径；`BLOCKED` 需大范围不同架构或授权设备。不要把历史步骤名、单一日志和按钮等同真实能力。

| 功能主线 | 产品源码状态 | 可复验资格/边界 | 施工后续 |
| --- | --- | --- | --- |
| 标准FakeTCP→TLS→保护认证→/32租约、原Go受控启动 | WIRED | HOST_PASS；旧API36达成TLS/租约 | 保留原入口；真服务端归属、E2E后验 |
| 原Rust Normal/off M1/M3/PN/M4 RAW/TUN双向、Health、owned Stop | WIRED | HOST_PASS＋旧API36 M4双向内核收据；业务字节E2E NOT_RUN | 优先解决真实业务阻塞与CPU，再追优化 |
| 原Root 选定普通App UID / 最多8 UID / all-app(20 profile)，单TUN与原路由精确Stop | WIRED | HOST_PASS；旧真机部分UID阶段通过；全App实机NOT_RUN | 修正多种UID范围仍没统一的IP例外，补kernel Host验证 |
| 原Fixed FEC2 TX parity、RX恢复、M2 Quality、DF0/DF1 PMTU | WIRED | HOST_PASS；Fixed物理E2E NOT_RUN | 不再造新的FEC2算法；补现有组合缺口 |
| 原Auto 低频策略、revision quiescent change、App REQUESTED/APPLIED回读 | WIRED | HOST_PASS；实体Auto稳态/换档 NOT_RUN | 原生性能验收前不调策略阈值 |
| 普通App IPv4 TUN→1.1.1.1 UDP53、反向映射，跨Normal/Fixed/Auto | WIRED | B29b HOST_PASS；系统netd不是入口 | 不重做已有64槽；验App DNS |
| 普通App IPv4 TUN→223.5.5.5物理 UDP53、CN8503分流与TCP53原隧道透传 | WIRED | HOST_PASS；只覆盖TUN内App包、TCP53不是物理直连 | 保留已有Socket/M3；后续按真实需求完善物理TCP |
| LAN-only Wi-Fi/Ethernet/蜂窝、同选定Network域名启动 | WIRED | B28b HOST_PASS；LAN手机 NOT_RUN | 使用现有Network，不新建resolver |
| App选择、设置持久化/SAF导入导出、凭据加密保存、TLS CA选配、诊断 | WIRED；B32完整已安装普通App枚举 CANDIDATE | 旧B26只显示有桌面/分享/HTTPS入口App；B32 Root APK加当前用户全安装包枚举、原UID复核不变；签名APK待本SOURCE | 真机App选择与Play分发资格NOT_RUN，不重复Root壳 |
| Android系统Resolver/netd UDP/TCP/DoH交付 | MISSING | 普通App TUN DNS ≠ netd DNS | 需要独立准确方案，不能声明已经全局拦截 |
| Android IPv6/464XLAT/IPv6 DNS全链 | MISSING | 当前TUN/租约/内核规则为IPv4 | 独立双栈架构；不要将AAAA解析误作IPv6可用 |
| Android Game2/Game4 原多lane TLS→Rust Game M4双向 | MISSING | Linux/Windows已有原Game，不等于Android端口 | 真正端口并接共享TUN后再开放App选项 |
| Android应用TCP/UDP双端逐字节E2E、切网恢复、低CPU/吞吐/首包 | NOT_RUN | 旧API36只有内核数据收据与用户主观“数据通了” | 必须有设备授权后验；此期不假造 |
| Android物理TCP53、原生业务IP直连例外 | B31 WIRED_CANDIDATE | TCP53已有原隧道；all-app既有server /32，单UID/组UID同原Go peer/32的throw已施工、待CI | 独立直连CIDR、Android真实netd、物理TCP53仍缺 |
| Android轮换/动态换物理Network、热点共享/Tether | BLOCKED | 原Go Linux rotation存在，Android明确禁用；Network loss只Stop | 后续独立源路径；不因可选参数存在而宣称实现 |

## 本批执行选择

优先做**同源原路由的3种普通App UID范围（单/组/all）与物理服务端IPv4例外**，补上原selected/group当前缺的Route `throw peer/32`；保持真实连接、自动/32、TUN、DNS、Stop不变。此为Android内核FIB生效路径、需跟已有rootjournal同生命周期，绝不用Go逐包处理。若该批Host验证通过，下一批再按依赖扩大“明确用户选定的真实IPv4直连前缀”，不代替系统Resolver和游戏端口移植。

维护：本台账是**进度标记**，不是独立竞争执行方案；每批以SOURCE/Action更新行，既往NOT_RUN/FAIL不删。
