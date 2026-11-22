# Android Root 原产品功能施工台账（B30｜源码与设备分层）

- **B35在建**：已选物理DNS IPv4不再仅接原Rust M4 App UDP53，也接原Go `--peer-host` 的冷UDP53/TCP53服务器域名引导；原 `Network` 绑定不变，默认223.5.5.5，不新增系统netd接管。Host/签名APK/实体资格依B35新SOURCE Action独立认定；Game/IPv6/热点/实体E2E仍缺。

- **唯一工作分支**：`experiment/android-temp-root-probe`，对照基线 `f115ab1840f1c50eb1922f9c34b67267ca1fd770`，Draft PR #36。主线 `main` 不写。
- **证据**：[B33c Android Dual64 #44975823370](https://github.com/lly8666/wbd-next/actions/runs/44975823370) **11 SUCCESS/4 SKIPPED**，包括签名ARM64 APK、原Go/Rust双ABI、Linux原服务端Oracle与原rootjournal全套Host测试；[Governance #44975823362](https://github.com/lly8666/wbd-next/actions/runs/44975823362) SUCCESS。Android真实应用E2E/性能依旧未验。
- **口径**：`WIRED` 源码确实连入生产调用链；`HOST_PASS` 同SOURCE已有Host/ARM64编译资格；`PHONE_PARTIAL` 旧真实API36片段凭据；`NOT_RUN` 手机/真实双端业务未验；`MISSING` 确认无生产路径；`BLOCKED` 需大范围不同架构或授权设备。不要把历史步骤名、单一日志和按钮等同真实能力。

| 功能主线 | 产品源码状态 | 可复验资格/边界 | 施工后续 |
| --- | --- | --- | --- |
| 标准FakeTCP→TLS→保护认证→/32租约、原Go受控启动 | WIRED | HOST_PASS；旧API36达成TLS/租约 | 保留原入口；真服务端归属、E2E后验 |
| 原Rust Normal/off M1/M3/PN/M4 RAW/TUN双向、Health、owned Stop | WIRED | HOST_PASS＋旧API36 M4双向内核收据；业务字节E2E NOT_RUN | 优先解决真实业务阻塞与CPU，再追优化 |
| 原Root 选定普通App UID / 最多8 UID / all-app(20 profile)，单TUN与原路由精确Stop | WIRED；B31三范围服务器/32例外HOST_PASS | B31正式签名APK/原Linux Oracle 11 SUCCESS/4 SKIPPED；全App实机NOT_RUN | B33扩展同私有FIB显式直连CIDR，无新逐包路径 |
| 原Fixed FEC2 TX parity、RX恢复、M2 Quality、DF0/DF1 PMTU | WIRED | HOST_PASS；Fixed物理E2E NOT_RUN | 不再造新的FEC2算法；补现有组合缺口 |
| 原Auto 低频策略、revision quiescent change、App REQUESTED/APPLIED回读 | WIRED | HOST_PASS；实体Auto稳态/换档 NOT_RUN | 原生性能验收前不调策略阈值 |
| 普通App IPv4 TUN→1.1.1.1 UDP53、反向映射，跨Normal/Fixed/Auto | WIRED | B29b HOST_PASS；系统netd不是入口 | 不重做已有64槽；验App DNS |
| 普通App IPv4 TUN→223.5.5.5物理 UDP53、CN8503分流与TCP53原隧道透传 | WIRED | HOST_PASS；只覆盖TUN内App包、TCP53不是物理直连 | 保留已有Socket/M3；后续按真实需求完善物理TCP |
| LAN-only Wi-Fi/Ethernet/蜂窝、同选定Network域名启动 | WIRED | B28b HOST_PASS；LAN手机 NOT_RUN | 使用现有Network，不新建resolver |
| App选择、设置持久化/SAF导入导出、凭据加密保存、TLS CA选配、诊断 | WIRED；B32完整已安装普通App枚举HOST_PASS | B32a同SOURCE双ABI＋签名APK/Linux Oracle 11 SUCCESS/4 SKIPPED，仍非手机可见性验收 | B33增加可保存/导出非秘密直连CIDR冷表单 |
| 全App额外按已安装普通App绕过 | **B34 HOST_PASS / BUILD_PASS** | 同源B34a原Go/Rust双ABI+签名ARM64 Root APK+Linux Oracle **11 SUCCESS/4 SKIPPED**；复用原20 profile UID FIB/8排除AppID配额（必含本App/KernelSU Manager），用户额外最多6包；App/SAF→Service双UID冷核验→原Go/journal精确Stop | **Android真机NOT_RUN**；跨profile同AppID可能共同绕过，实际物理出口未验 |
| 物理DNS可选IPv4上游 | **B34 HOST_PASS / BUILD_PASS** | 同源B34a 11 SUCCESS/4 SKIPPED；App/SAF→Service→Go冷参数→原Go/Rust M4冷设置/逐字节读回→已有Android绑定Network UDP53 Socket；默认223.5.5.5，可选LAN路由器IPv4 | **实体UDP53查询/E2E NOT_RUN**；系统netd/DoH、原Go冷服务器引导、物理TCP53均非此路径 |
| Android系统Resolver/netd UDP/TCP/DoH交付 | MISSING | 普通App TUN DNS ≠ netd DNS | 需要独立准确方案，不能声明已经全局拦截 |
| Android IPv6/464XLAT/IPv6 DNS全链 | MISSING | 当前TUN/租约/内核规则为IPv4 | 独立双栈架构；不要将AAAA解析误作IPv6可用 |
| Android Game2/Game4 原多lane TLS→Rust Game M4双向 | MISSING | Linux/Windows已有原Game，不等于Android端口 | 真正端口并接共享TUN后再开放App选项 |
| Android应用TCP/UDP双端逐字节E2E、切网恢复、低CPU/吞吐/首包 | NOT_RUN | 旧API36只有内核数据收据与用户主观“数据通了” | 必须有设备授权后验；此期不假造 |
| Android物理TCP53、原生业务IP直连例外 | **B33 HOST_PASS / BUILD_PASS** | 同源原Root私有table 19842最多4个真实CIDR throw，单UID/组UID/all-App同原journal/Stop；App→Service→Go CLI→真实ip规则命令Host PASS；签名APK PASS | **Android实体netd后续物理路由NOT_RUN**，物理TCP53仍MISSING |
| Android轮换/动态换物理Network、热点共享/Tether | BLOCKED | 原Go Linux rotation存在，Android明确禁用；Network loss只Stop | 后续独立源路径；不因可选参数存在而宣称实现 |

## B34 本批执行选择

上一B33c `dd2292c8` [#44975823370](https://github.com/lly8666/wbd-next/actions/runs/44975823370) 原Go/Rust/签名APK/Linux Oracle **11 SUCCESS/4 SKIPPED**。本批大类优先做**全App模式按已安装普通App额外绕过**与**真正物理UDP53上游IPv4可配置**，全部复用原Go/Rust、原持久UID FIB、原Rust物理绑定socket。B34a源 `d70132608bf5` [Android dual64 #44978243692](https://github.com/lly8666/wbd-next/actions/runs/44978243692) **11 SUCCESS/4 SKIPPED**，包括完整签名ARM64 APK、Go/Rust双ABI与原Linux Oracle；[治理 #44978243728](https://github.com/lly8666/wbd-next/actions/runs/44978243728) **SUCCESS**。不新建Go逐包Worker、Android系统resolver劫持或大型CI。

## 原B33完成的软件资格

B31已补服务端IPv4 /32例外；B32a已补完整普通App选取。**B33**进一步批量施工显式最多4个IPv4 CIDR的真实内核FIB直连例外：原Root Activity设置（可本机保存及SAF导入/导出）、原Service手动START、原Go冷参数、single/group/all原journal路由安装/读回/Stop、Host原伪ip内核命令回归，全部同一SOURCE。默认输入空保持原WBD全隧道，无新增Go/Rust逐包控制器。最新B33c SOURCE dd2292c8f9ca [#44975823370](https://github.com/lly8666/wbd-next/actions/runs/44975823370) 11 SUCCESS/4 SKIPPED，正式签名APK/Host/原Linux Oracle均PASS。真实手机netd/实际物理出站、应用E2E及性能仍NOT_RUN。

维护：本台账是**进度标记**，不是独立竞争执行方案；每批以SOURCE/Action更新行，既往NOT_RUN/FAIL不删。
