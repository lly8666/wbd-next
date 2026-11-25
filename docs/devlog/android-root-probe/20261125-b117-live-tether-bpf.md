# B117｜真实共享 BPF 挂钩会话暂停与归还

B116 SOURCE `38419091fa94ab86ab8fe1f71e259f6a7ca16ce0` [Action 45588147383](https://github.com/lly8666/wbd-next/actions/runs/45588147383) 13 SUCCESS / 0 FAIL / 9 SKIP。实际硬件设置 owner Host 测试、ARM64签名APK及Normal独立原peer业务通过。B115 [Action 45583719117](https://github.com/lly8666/wbd-next/actions/runs/45583719117) 14/0/8，API35/36真实十槽/MTU保存通过。用户上传B115真机报告先 HARDWARE_OFFLOAD 后 BPF_OFFLOAD；后者也可能是未知状态，并非已证明全部OEM BPF运行。治理独立失败保留。

用户新授权连接时暂停共享BPF、断开恢复。AOSP BpfCoordinator的mIsBpfEnabled构造时决定；运行中写配置不等于停止。参考 https://source.android.com/docs/core/ota/modular-system/tethering 和 AOSP BpfCoordinator/BpfUtils。选择只摘除真实 AOSP tethering ingress TC BPF offload hooks，保持原程序、maps、其他系统BPF及配置；无需重启网络服务。NETLINK_ROUTE读取接口、原handle/priority/protocol/flags/name/program ID；BPF_OBJ_GET和GET_INFO核对原pin仍为相同程序后才摘除，确认两个IPv4方向和读回。持久会话journal用于原Stop和恢复网络；同一boot且原接口仍在才归还；重启后的旧接口不重放。已明确关闭不写。未知OEM、XDP或不可复原的程序不冒充支持。硬件独立owner仍遵守已运行HAL不假定可热停。

原共享下游及forwarding检查先行，BPF pause完成才进入原连接，授予转发路由前再核实。订阅内核TC/link事件，若正常拓扑变化导致共享挂钩重挂则取消原会话，随Stop清理后归还，避免持续沿旧拓扑工作；非逐包检查、无定时轮询。未证明事件通知覆盖所有OEM路径或切换瞬间零绕行。正常断开、冷失败归还；清理失败留journal供现有恢复网络入口，不宣称杀进程必然自动恢复。普通连接不启动BPF owner/watch。协议、TLS、FEC、RAW/TUN与热路径不改。

验收计划：host真实owner生命周期；x86 KSU guest用原AOSP pinned tether programs附着到独立veth，使用生产代码摘除、重挂通知、归还并验证相同ID；再一独立Normal实际业务回归。该guest测试不是实体热点/USB终端端到端；ARM64 APK仅签名构建，物理机和设备具体pin/权限/HAL尚待验证。main未改，PR36 Draft。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Session-owned pause and restore of observed native AOSP tether BPF attachments, with event-driven topology lifecycle and actual Android kernel fixture."}
```
