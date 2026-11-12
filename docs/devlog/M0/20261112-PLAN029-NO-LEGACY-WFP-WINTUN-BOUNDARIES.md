# PLAN029｜不接老WFP，明确Wintun真正边界

用户最新指令：不接入旧项目WFP体系，并核查Wintun限制会否阻碍新分流。审阅main f873cfef的真实Windows入口、固定五阶段事务及官方Wintun API。

本记录**替代同日上一记录的“修改旧Block加例外”实施决策**，历史源码发现保留。029新正式路径不Arm旧guard，也不以假guard回执蒙混；同步移除入口、固定stage、Ready和Stop对WFP的必需依赖。只保留精确owned旧对象一次性清理，不动系统/第三方防火墙。已有原值/owner恢复资料保留。

Wintun自身不要求WFP；真正需遵守的是IP层数据、RX借用及时释放、TX分配顺序、事件等待/有界ring和Stop生命周期。特别要求先备好数据再AllocateSendPacket立即提交，不持ring槽等待DNS/远端IO。租约/MTU/generation保证转发正确；局部辅助地址如有必要是本机owned资源，不篡改服务器认证租约。

能力边界：系统DNS和实际进入Wintun的流量按新策略；不声称仅靠少量路由能拦截任意on-link/绑定物理/加密DNS。原IPv6阻断仍需实际验证，不以去掉WFP冒充全覆盖。以上完整写入契约§3A，并同步029/M0提示、功能卡、cursor。无产品修改、无网络dispatch，实施及实网NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Latest user removes legacy WFP integration requirement; document required dependency removal, owned historical migration and real Wintun ring/API constraints, with honest DNS/IPv6 qualification boundaries."}
```
