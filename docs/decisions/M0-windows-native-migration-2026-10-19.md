# PLAN-010：Windows运行时去PowerShell的定向迁移

2026-10-19用户要求核对老项目后续去脚本内容、规划移植及相关工位临时任务。本页补充PLAN-008/009与MIGRATION；是可实施决策，不是已完成移植或新的产品PASS。M0合并后按第5节发布临时包，worker不能靠本文自扩权限。[精确差异和事实](../evidence/M0/PLAN-010-windows-native-migration.json)。

**用户最新收口要求（覆盖本页先前的多代理/极端场景要求）**：产品环境按“一台电脑同一时刻只运行一个网络代理相关实例”设计。M4负责把全部产品运行时去PowerShell工作做完，不能只交原生helper或迁移清单；M0一次发布M4最新Windows Actions自主测试入口和权限。无需支持多VPN/多Wintun并行接管、第三方同时改网络、极端PnP ghost自动修复。正常错误、取消/退出、一般异常终止后的owned恢复仍保留；检测到明显不满足单实例前提就清楚拒绝，不实现共存协调系统。构建/Actions开发脚本可继续使用PowerShell。

## 1. 审查结论：组件很多已在基线，完整运行时去脚本尚未完成

- wbd-next固定冷层基线：`a7a82db31fe736ffedee330795a3234d358f1984`。
- 老仓库 `lly8666/wobuzhidao` 的 `next/adaptive-fec-aes-tun-20261010` 本次HEAD：`6ec6b5836c2b70a85f2ef89c2f5ea4525c6ed340`；最后相关产品修改 `c57ea67cdde2be6dcc2e39b5bcfeb7d63363af99`。后继d4f605/6ec主要是CI/记录，不能当新运行时资格。
- 基线已经有原生IP Helper路由/地址/MTU、DNS API、WFP归属检查、五阶段事务/WAL、机器锁、创建者归属和大部分Wintun恢复组件，以及TUN内分类/Direct基础。不是从PowerShell零重写Windows网络。
- 基线到最新：`internal/windowsclient/`只有**12个相关变化文件，6个产品文件+6个测试文件**，其中4个新增；go.mod/go.sum无变化。主要补PnP设备实例指纹写入第一份WAL、精确旧Wintun校验、ghost DNS有限CAS和lease只读审计。逐文件base/donor Git blob已记录。
- 老版最新仍存在：`cmd/wbd-client/main_windows.go`的Apply/Cleanup启动powershell.exe；`windows/gui/MainForm.cs`的RecoverAsync启动.ps1；`Portable.cs`自动注入network-script，GuiTests要求脚本路径。
- `native_unified_assembly_windows.go`仍置 `assemblyOnly:true`；`native_wfp_guard_windows.go`的生产Arm仍直接拒绝。旧的“除本Wintun外全部接口”规则会误伤其他Wintun，不能只删拒绝/翻布尔开关放行。
- donor的N4/N5 Actions是有范围的native/unit/race成功：ghost DNS清除/lease缺席审计成功，**MTU行缺失情况下的完整崩溃恢复仍UNSUPPORTED**，生产WFP、两条/1接管、真实Direct/完整产品/物理未通过。不能用workflow绿灯冲掉这些缺口。

**迁移路线固定**：保留a7a82冷层主基线，精确补入12文件及依赖闭包，再把现有Go原生事务接到真实CLI/GUI。Windows冷层继续Go，不为去脚本改写Rust、引入新驱动或搬回旧Go数据面。优先正常启动/停止/恢复，罕见PnP ghost保持明确失败与日志，不重开无限研究。

## 2. 具体导入方法：原基线 + 小型donor增量 + 本项目接线

1. M4先审查差异表及调用闭包。6个产品文件为：
   - `native_orphan_ghost_dns_windows.go`、`native_orphan_ghost_lease_audit_windows.go`（新增）；
   - `native_orphan_persisted_preroute_windows.go`、`native_orphan_pnp_probe_windows.go`；
   - `native_unified_assembly_windows.go`、`native_unified_network_transaction.go`。
   配套6测试见证据JSON；首次整体保留同一donor版本，不只挑DNS helper丢掉PnP/WAL前提。后续明确移除死代码才按新实现留证。
2. 使用现有 `r0/go_overlay/assembly/manifest.json` / `assemble.py` 装配。donor文件进入M4新增授权的 `r0/go_overlay/internal/windowsclient/`；已有文件必须核a7a82原blob，新文件必须不存在。必要时仅扩现有replace操作支持“精确原blob→overlay完整文件”，禁止模糊patch或覆盖无关文件，不建第二个装配器。
3. 清单记录base SHA、donor SHA、每文件原blob/donor blob/最终blob及本项目修改理由；最终产物同时记录实际Rust SOURCE、cold base、delta、overlay SOURCE。新接线改变导入文件后保留donor依据，最终hash重新生成。不能沿用旧manifest里的rust_source常量冒充实际构建。
4. 只在Actions的临时旧源checkout组装；旧仓库/main、原发布基线、旧AGENTS/STATUS/几千行日志不导入或改写。本项目参数目录/治理仍唯一权威。**不全局移动r0/source-lock的legacy SHA**，避免顺带重测所有旧向量、bootstrap和Linux路径。
5. 导入delta先做受影响包的编译/功能/race，再接CLI/GUI。原生低层函数和恢复语义可以复用，旧版“未接线/UNSUPPORTED”不会因复制自动消失。

## 3. 产品接线架构与必须修好的边界

### 单一Go网络事务，GUI只调用客户端

- 在 `internal/windowsclient` 给现有事务提供最小产品门面：预检/应用/清理/恢复/状态。沿用NetworkPlan与五阶段WAL，不增加常驻服务、后台脚本、第二份状态机或逐包RPC。
- CLI的Apply/Cleanup直接调用Go原生门面，取消后用独立有界cleanup context；native系统调用不一定可被context强行打断，不能只启动遗留goroutine后报已完成。串行事务、机器归属锁和未完成状态必须可恢复；超时返回明确原因，禁止假成功。
- GUI正常连接/停止走现有client控制通道。恢复按钮可调用同一portable `wbd-client.exe` 的明确恢复子命令（建议 `--recover-network`，实际以参数目录统一），传状态路径，返回结构化结果/退出码；不再启动PowerShell，也不在C#复制路由/DNS/WFP逻辑。并行读取stdout/stderr、有界等待，避免重演当前GUI自测未等待进程结束的问题。
- 数据面停止关系：停止新业务接入/控制更新→Rust owner quiesce并释放借用/设备I/O→清理owned网络→关闭TUN与进程。M0接现有Stop完成回执，不新增热路径逐包跨语言调用。lane rotation、payload-idle仅关闭/重建lane，不重复删除TUN或重装全机路由。
- GUI准确显示正在清理、部分恢复、冲突/不支持及重试入口；不能永远busy，也不能网络未还原就显示已断开。重试只处理精确owned对象，不能按adapter别名找另一块网卡接着清。

### 原生网络行为必须与现有用户目标一致

- 地址租约、MTU、路由沿IP Helper；DNS沿已有原生Get/Set接口与快照回读；WFP仍用已有成熟封装。应用前记录意图、写入后读回；撤销比较当下状态与本程序写入值，仅恢复自己实际更改的值。其他程序中途更改则报冲突，不覆盖。
- 保留DNS 1.1.1.1/8.8.8.8互备、借站/服务器/Direct出口旁路，IPv6默认拦截、LAN/可选中国IP用户态分流与少量系统引导路由。不是零条Windows路由，也不能把CIDR表再次展开成数千路由。
- 不重写Direct TCP/gVisor/UDP实现、不新增WFP callout驱动或WinDivert路线；本包只保证已有Direct与原生网络管理的出口/生命周期接口一致，其真实业务通过性按测试范围报告。
- native能力预检包含实际OS/API、管理员权限、当前接口身份和基本状态可恢复性；任一不满足在写系统状态前明确返回。使用现有机器级实例锁防本程序重复启动；不开发第三方代理检测大全，也不证明未来任何软件都不会插入网卡。
- **WFP按用户明确的单代理运行环境收口**：复用旧规则规划与owned API，核清作用域/方向/地址族/DNS覆盖和必要旁路，完成原生读回及正常撤销后可用真实事务替换Arm恒拒绝/assemblyOnly。旧“不能与其他Wintun共存”不再是本包必须解决的产品阻塞；不做多代理仲裁、共享过滤规则或动态多TUN白名单。系统DNS/IPv6必须实际受控，不能只过滤本exe就宣称全局行为完成。
- 正常网卡/出口变化沿既有事件重新预检，恢复失败有界退出并保留owned状态，不建设极端热插拔自愈系统。仍不能仅删guard拒绝而不实现/验证真正Apply和Cleanup。单代理产品前提不等于可以切断Actions宿主的管理网络，完整接管的隔离要求只约束测试环境。**正常场景通过就收口，Linux与其他模块接线继续独立进行。**

### 状态兼容与portable

- 原脚本journal与native WAL分格式/版本。首次升级有旧状态时先识别：支持精确解析/回读的字段可一次性用原生恢复；无法证明归属则拒绝新Apply，给旧版恢复说明，不删文件、不静默混用journal，也不隐式回退脚本。
- ghost仅DNS恢复成功、MTU行不存在，仍是部分恢复；保留必要WAL/归属信息，不能据“查不到接口”宣布MTU已还原。该已知异常保留一个反例与明确UNSUPPORTED，不逐代研究更多PnP排列。
- 普通程序运行不释放/依赖.ps1，不启动powershell/pwsh/cmd/netsh/route去管理网络；更换解释器不算完成。构建、Actions、维护开发脚本可以保留，Npcap/Wintun既定安装例外不变。
- 移除Portable.cs对network-script的自动注入，更新CLI/help/配置/GuiTests/唯一PARAMETERS和打包清单。已有用户配置的network-script仅作可见弃用迁移提示；自定义脚本不执行，不留运行时备用脚本开关制造两套维护路径。
- 状态/日志/temp继续在程序目录；OS本身的网络对象/驱动状态不是“释放临时脚本”。正常恢复可调用同目录exe，不额外装服务，不以路径变化绕过owned状态验证。

## 4. Actions验收：一批功能、必要同机成本，范围清楚

| 验收组 | 必验内容与边界 |
|---|---|
| 装配/源码 | 12文件base/donor/final hash，错blob/重复目标/越界拒绝；最终原客户端/GUI真实构建，不只是helper；原Linux/ARM装配不退化 |
| 纯状态机/race | 正常Apply/Stop/Recover、每阶段已知失败/取消、重复启动拒绝、部分写入、旧journal/坏WAL不误清理；合批，不为极端并发/第三方篡改新建矩阵 |
| Windows native | windows-2022与windows-2025，真实API/单实例owned Wintun/原生回读与正常恢复；DLL/API不支持、无管理员清楚拒绝。多代理共存/极端网卡重建不作验收前置；两server runner不等于Win10/11物理资格 |
| CLI/GUI/runtime无shell | 启动→应用→停止→恢复走真实入口；跟踪**产品进程树**不得产生powershell/pwsh/cmd/netsh/route网络子进程（Actions宿主shell不算）；删除发行目录.ps1仍能执行；退出码和真实完成收据，防仅静态grep或渲染测试刷绿 |
| 隔离完整网络 | 在已证明确有隔离的Windows来宾/专用可恢复环境中，少量server旁路+capture路由、DNS双备/主失效、IPv6拦截、LAN/中国分流、Direct TCP/UDP、断开恢复和崩溃后重新启动；实际业务和系统回读结合。未有隔离不能在承载CI管理连接的宿主装全机WFP/默认路由 |
| 停止/热路径保护 | 有业务时Stop/连接失败回滚、休眠后唤醒、rotation不重装网络、TUN借用归还；原有无HOL/MTU/FEC/cipher参数不变，不把去脚本变成数据面重写 |

优先复用旧native admin/owned transaction用例和当前M4原产品/GUIworkflow，由M0给公共Windows执行入口，M4自行发request/验结果/修复。正常路径、实际无shell、恢复和必要参数生效成立就停止加样本；极端场景仅保留已有证据/UNSUPPORTED，不新开发。不要复制旧项目整套八十个workflow。运行时去脚本不要求将CI PowerShell转写另一语言。

隔离不可用时明确完整Windows网络 `NOT_RUN/UNSUPPORTED`：继续完成组件/构建/CLI语义与正常恢复；报告具体缺口，不无限换runner刷ghost结果，也不能让模拟PASS代替缺的完整门。物理测试另排，不由本包自动部署用户机器。

**性能**：收益主要是连接/断开/恢复的进程创建、CPU/内存和可靠性，稳态吞吐未必明显提高。必要时在同一Windows job、同场景/配置做旧脚本与新native顺序A/B，构建一次复用，测各阶段wall/CPU、峰值RSS、子进程数、系统对象数及回滚结果；两边业务/策略覆盖等价才可比。完整网络不具备隔离则不宣称产品启动性能已测，可先留组件观察。稳态只补一条有理由的既有性能锚点，不重跑全档FEC；不得新增周期扫描、per-packet注册表/Go系统查询或用关闭保护换速度。不同runner间CPU百分比不直比；容量不足停止更重测试，p99要同时报业务missing。

## 5. 临时任务发布与单一文件所有者

**先结算M4当前015与在途Actions，在安全交接点保留准确partial/ready事实；已有GUI修复PASS直接复用，不重复等待或重跑，随后切临时包。** 未完成的真正产品接线验收转入本包引用，不要求先伪称015全部完成，也不让M0/M4同时改同一个overlay。主线task/权限登记后才实施。

| 工位 | 临时职责 / 退出条件 |
|---|---|
| M4（全包负责） | `R5-M4-NATIVE-WINDOWS-NETWORK-016`：完成所有产品运行时去PowerShell，包括CLI连接/断开/恢复、GUI按钮/配置/portable、旧脚本引用/依赖清除及自主Actions验收。单代理正常工况完成即可，不只交helper，也不等极端ghost完全自愈 |
| M0（一次配套） | 在025登记M4新包/路径，给M4当前可用的Windows Actions自主触发/读取产物/修复复测能力；补共享Stop接口与最终集成。入口未支持M4必须先补，不只口头授权。保留产品工作，不亲写M4文件、不逐条代跑 |
| M1 | **无默认新包**；仅当M0发现真实quiesce/设备借用契约缺口时，在其模块现有职责内给一个有复现的最小修复；不能提前为此重写runtime |
| M2/M3 | **无新增任务**，继续当前验收/交付；不改恢复/FEC/加密/报文 |

M4建议唯一新增allowed_path：`r0/go_overlay/internal/windowsclient/`；其CLI/GUI/config/PARAMETERS/scripts/assembly已有权限。必要新增native Windows参数测试也放该路径，不开放整个internal/或runtimeentry/realityfront。root source-lock/deps/公共ABI/workflow仍由M0；若出现新依赖先证明为何已有x/sys、wf与原库不能满足。donor增量本身不需要改go.mod/go.sum。

### M0必须一次开通M4实际可用的最新Actions入口

核到main `fff6d04`时，`worker-component-validation.yml`的adapter/role校验仍只支持M1/M3；`m0-m4-product-assembly.yml`支持push/中央scope完成自动触发，**尚无workflow_dispatch**。不能让M4照抄M1/M3请求再撞拒绝，也不能靠无关提交蹭自动跑。

M0优先给现有M4产品workflow补手动请求入口，或在公共入口补M4 Windows adapter，二选一复用，不重复建两套。一次登记实际workflow、固定control ref、M4 role/task、精确request/source/scope回执、Windows目标和artifact入口；正常无变化源码可复用已有构建。提供一个真实可执行示例并在Actions验证身份/来源和调用链。保留自动触发时先查同源码同范围在途run，避免手动重复。

M4在包内自行提交intent、dispatch、下载核验、修复和重新请求，不等M0合并每个源码或代跑；功能Windows矩阵可批量，性能仍一Action一场景/一个测量job、同机旧新顺序。若聊天凭据确实缺dispatch权限，M0明确补实际执行通道，不通过扩大worker共享源码写权限替代。公共workflow维护仍M0，场景/夹具仍M4。该入口发布是M0短前置，不以所有极端场景齐全为条件。

M0在一个登记提交里给goal引用本文、done_when写真实能力/NOT_RUN边界；沿既有revision/epoch规则，不无故重置所有工位。先核在途请求，保留旧合法run的精确来源，新的请求用最新登记。**不改长期提示词、不代写worker cursor、不另起新聊天/任务数据库。**

## 6. 实施顺序与可回退点

1. M0发布；M4核并记录015当前实际结果，固定源码/任务/增量。
2. M4导入12文件+断言、实现门面与旧状态识别；先组件验，旧基线可回退。
3. M4完成正常原生网络/有限guard候选和CLI/GUI/portable接线，M0补唯一Stop/公共CI缺口。不得发布默认打开的未验guard。
4. M4自主Actions验功能/必要成本，失败定位到所属包；只在明确隔离环境跑全网络。M0消费精确产物集成，并分别记录Windows native activation与Rust产品能力。
5. 达到能力退出条件就收口。发行包去.ps1要与真实运行资格同时成立；否则保留实验gate和清楚的缺项，不将“编译成功/不再启动shell”单独当网络可交付。

## 7. 来源与API约束

- donor记录：[N4有限恢复](https://github.com/lly8666/wobuzhidao/blob/6ec6b5836c2b70a85f2ef89c2f5ea4525c6ed340/docs/devlog/20261014-n4-ghost-lease-readonly-scoped-actions-final.md)、[N5范围与未完项](https://github.com/lly8666/wobuzhidao/blob/6ec6b5836c2b70a85f2ef89c2f5ea4525c6ed340/docs/devlog/20261014-n5-scoped-integration-actions-final.md)。旧完整STATUS过长，不复制到本仓库热入口。
- [Microsoft SetInterfaceDnsSettings](https://learn.microsoft.com/en-us/windows/win32/api/netioapi/nf-netioapi-setinterfacednssettings)列Windows 10 Build19041最低客户端要求；仍需runtime API/实际target检查，不以编译目标替代兼容资格。
- [WFP条件定义](https://learn.microsoft.com/en-us/windows-hardware/drivers/network/filtering-condition-identifiers)区分local/forward interface LUID；不同层可用条件不同。guard必须查实际层支持并验方向，不能凭LUID字段名字推断能隔离全部流量。
