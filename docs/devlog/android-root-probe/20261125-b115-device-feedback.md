# B115｜真机反馈：设置保存、十服务器槽、热点/USB连接故障定位

B114 SOURCE `d89db3b13c4de73773a55822fe25671b4bc14813` [Action 45577319665](https://github.com/lly8666/wbd-next/actions/runs/45577319665) 19 SUCCESS / 0 FAIL / 8 SKIP，8个同源独立x86 Android guest均PASS，七模式真实远端普通业务及原Stop、Normal隧道DNS/生产自动重连、Fixed/Auto轻损恢复反馈、Game4 Fixed轻损业务与恢复候选。CI专用载体不代表实体物理性能。用户反馈B113 ARM64/API36真机大链路通、分流初测正常，未仔细验证其他项目。

用户明确三项：设置页保存参数、服务器十槽、勾热点/USB共享后连接失败。B115 复用原SettingsStore：设置页明确按钮，保存实际outer MTU与其他冷参数，现场读出已保存MTU及模式、下次连接生效；另显式同步所选同服务器槽（peer/port/SNI/account一致），保留该槽原密码、RouteKey和CA，不改运行中会话。十槽统一UI/文件/Keystore/CA/冷切换/备份；原1–4文件及旧4槽bundle继续兼容，旧bundle只恢复1–4，5–10保留，新备份含10槽且不含秘密。Host十槽/旧bundle/槽10冷切换、API35/36真实UI 1380保存/进程重启及槽10参数更新1400，普通连接回归一次。新SOURCE待CI。

用户提供的脱敏诊断：B113 API36最后一次四lane真实TLS/Admission，已出现authenticated lease读回，随后exit1、未见UID/M4 READY；旧报告误标SYNACK缺失/lease未证。相符于postauth路由/共享阶段失败，未包含具体tether错误，不能断言根因。原B65只支持软件转发，要求活动下游、ip_forward=1、硬件offload明确关闭及BPF不活跃；当前设备具体状态未证。B115将原只读准入提前至TUN/SYN前，并保留实际grant前重新核对；固定诊断类DOWNSTREAM/FORWARDING/HARDWARE_OFFLOAD/BPF_OFFLOAD/DNS_BIND/KERNEL_RULES/POSTAUTH_ROUTE及UI明确提示，纠正Game已经lease却报未见SYNACK。无默认关闭BPF/netd/offload、无静默降级或物理路由绕过、无更改TLS/MTU算法/数据面。不宣称已修复实体共享承载：仍需同设备新诊断定位究竟是offload准入还是实际转发规则；若BPF启用，该路径当前不支持。用户真实报告TLS证书校验关闭，保持原用户选项不静默修改，建议启用严格校验。诊断原文件不入库，不含账号/地址/密钥。main未改，PR36 Draft，历史governance失败保留。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Real device feedback: explicit settings-page persistence and ten compatible server profiles; early software tether eligibility and precise safe failure receipt."}
```
