# PLAN029｜按功能需要精简防御约束

用户要求检查多余安全限制，保持自用项目简洁、性能优先。本次审阅main `3d94e0bac2fa739e000a1e78e31cd952d927f9cc` overlay、原Go a7a82db装配基线的WFP builder/validator和实际Recover代码，**只更新施工要求，不动正在开发的产品代码、不派发Actions**。

源码发现：原guard对非Wintun remote53 Block，没有拟新增Direct DNS socket的例外；原验证器固定3条Block，overlay精确Arm也拒绝Permit；统一Recover在其他资源恢复前要求完整guard仍Owned。这些旧设计可阻碍新增DNS出口或异常清理。尚未拿此结论冒充新Direct DNS实网失败；当前Npcap冷bootstrap不同于拟新增普通Winsock业务DNS。

[分流契约§3A](../../architecture/CLIENT_SPLIT_DNS_CONTRACT.md)明确修改最小owned规则范围、同步验证/装配、独立已确认资源清理，不盲叠全局Permit，不动第三方规则，不重构整套WAL。保留正确出口/IPv6/认证/完整性/generation/长度/原密文；不新增抗本机攻击、多代理或逐包权限检查。冷路径校验不冒充稳态CPU热点，测试只并入D1/D4代表场景。

已同步029、M0-029提示、功能卡与cursor下一步，既有产品checkpoint/测试证据不变；新增修复与网测仍NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Document concrete legacy WFP DNS block and cleanup-precondition conflicts; authorize minimal functional policy updates without extra defensive frameworks. Product implementation/testing remains NOT_RUN."}
```

本次验证仅文档/功能登记/governance结构，产品未测试。
