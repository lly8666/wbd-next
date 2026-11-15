# 2026-11-16｜029B设计交付，产品未改

用户授权：将刚讨论的分流资源退出、FakeIP高级CN开关、IPv6方式整理为029B，关键边界写详细。初审main `601d540401b7d516bf1e1dfaa9c2998cce07defb` / H1940；不改M0活动源码、registry/cursor、在途Action或其测试资格。

交付：[PLAN029B](../../decisions/M0-PLAN029B-OPTIONAL-SPLIT-FAKEIP-IPV6-20261116.md)、[固定提示](../../prompts/M0-PLAN029B.md)。同步029/分流契约/启动入口/M0提示/分包导航与现有功能卡，避免旧“CN域名必直连、关闭FakeIP便不需要域名trie”等条款与新方案冲突。

关键事实：当前all有DATA快路但V3仍构造NativeSplitWorker；DNS、padding和回程依赖该对象，不能直接None/V2回退。CN当前耦合FakeIP分配与journal；AAAA空答主要CN路径。Linux openTun已仅禁自有TUN IPv6，Windows真实IPv6范围仍待既有D4证据。方案不把已实现内容重新开工，不把未知范围写PASS。

定案：旧split-enable加route-mode计算真实业务分流启停；公共DNS/padding独立；新canonical cn-domain-direct只决定CN域名强制Direct/FakeIP，普通CN查询仍按域名选DNS。新配置默认off，旧缺键迁移保行为。Windows保留IPv6绑定/接管后现有入口丢弃；Linux保留接口级禁用；所有受管AAAA立即NOERROR空答，不全封HTTPS/SVCB、不改宿主全局/旧WFP。

执行顺序：当前029冻结优化批次安全收尾→029B完整工作包→必要B0–B5和同VM保护→029剩余出口→已授权后续；不取消现有测试，不发其他聊天消息。本次隔离文档分支提交，经PR供M0消费，保持main单写。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","startup-flow-padding","gui-config-feedback"],"reason":"029B设计预登记与文档引用：可选业务分流、高级CN开关、公共DNS/填充解耦及IPv6政策；未修改产品默认值/实现/已有测试资格。"}
```

验证：文档引用/diff与JSON静态核对；Governance随push验证目录/结构。产品代码、网络/性能测试与物理测试均NOT_RUN；历史FAIL/NOT_RUN保留，不运行新的网络矩阵。
