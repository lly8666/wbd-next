# B101｜异构 Game MSS 冷态共同预算、真实异常恢复解阻、DNS6 新内核兼容

B100 SOURCE `471f9406b09d581e61ddc0c7e6f88cfc58b6e124` [Action 45530309154](https://github.com/lly8666/wbd-next/actions/runs/45530309154) 11 SUCCESS / 9 FAILURE / 6 SKIP。8 mixed MSS 场景4/8 PASS：四种 Game 最小MSS=1000位于首lane时TUN错误采用最后lane预算（off 1153而非953、fixed 1138而非938），位于末lane时4/4临界真实RAW和Stop通过、177包0超限（20+40+36+81）。原Rust GameAdapter以认证client/server共同record cap建组，原Android Go逐lane ConfigureTunnelMTU 会覆盖而且不能保证Rust group cap一致。B101在全部真实SYN完成后，从原 Rust MTU oracle 以最小peer MSS、原配置/物理/已有本地record offer派生初次 TLS 共同client limit；各lane同一原TLS认证，不改认证后cap、不改主程序公式；所有lane完成认证后统一一次ConfigureTunnelMTU，原native join前完成。8个原case及Game4中间/双低MSS各2 case，共12个；CI实际cold snapshot校验每lane认证limit，TUN/临界RAW/DF/Stop均独立。未将初次共同cap等同在线动态PMTU或独立方向RX调整。main不改。

4 crash case exit86 + 实际UDP TUN通过，DNS case真实Resolver也PASS；日志有遗留RPDB/throw/DNS NAT，但 adb shell su -c 多命令引号丢失，后续命令以shell UID执行，journal ls Permission denied，故原RecoverOwned NOT_RUN。B101仅CI改成已证分条完整su -c读回；必须真实独立进程恢复、物理两UID回显、原RecoverOwned重复幂等、外部kernel cleanup。无产品新防御/回滚机制。

B100 [DNS6 relay 138925182626](https://github.com/lly8666/wbd-next/actions/runs/45530309154/job/138925182626) 普通App IPv6 loopback UDP/TCP及原Bionic relay/physical DNS/Stop PASS；Android kernel IPv6 NAT仍ENV_BLOCKED。独立 [Linux netns 138923675911](https://github.com/lly8666/wbd-next/actions/runs/45530309154/job/138923675911) 实际rule已装但readback报selector29 length2。Linux upstream UAPI FRA_DPORT_MASK=29，fib_rules.c 对单一端口range默认U16_MAX；B101接受同义全位掩码，不改变原rule或扩大匹配范围，Host test兼容有/无mask。真实IPv6 namespace继续测试；不是Android IPv6系统NAT PASS。

B101 8独立guest（4 crash +4 mixed）12 mixed +4 crash场景，1真实host netns；已通过的B100 DNS6 relay不重复，B99 239 wire与双UID/CN证据保留。双ABI/基础Host回归同源。未证明真Android↔Linux SYNACK/TLS/lease/M4、remote RX/FEC recovery/READY自动切换；未改热路径/main/设备/外部服务器。governance历史失败仍在；新SOURCE待CI。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Record B100 actual mixed-lane order failure and DNS6 relay pass; fix cold common Game record offer/TUN apply, restore crash test admission and exact DNS6 port-mask compatibility."}
```
