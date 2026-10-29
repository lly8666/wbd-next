# PLAN027 用户授权：先去M2，再接线与矩阵

2026-10-30。本批仅方案/派工入口/长期提示词，未改产品、未执行产品测试或发送其他聊天消息。
- 取消线上高频Receipt，复用老版低频质量/Health和外层ACK/SACK机会重传；保留原密文/预算/完整性/Stop。
- Auto升档期无丢包硬门，充分有效低损持续业务120s降一档；矩阵10–200Mbps/最高30%/单程250ms，Game4最高FEC≤20Mbps，容量止步。
- 顺序变更为整批替代开发+A简化验证→B接线→C矩阵→证据驱动优化。每Action单测试控制进程，统一编译复用。
- M0默认中断恢复，先收在途结果；完成后重复定时提示只回报待验收，不刷矩阵。
- 基线main de892bb3，cursor H373可能落后后续提交；未篡改历史SOURCE/PASS/FAIL或代替M0结案。新计划/registry优先旧next_action。
- 后续由M0实现测试。文档自检只检查链接/JSON/差异，不当产品PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"User-authorized PLAN027 ordering, M2 retirement design, acceptance and durable M0 prompt only; no runtime behavior or recorded test results changed."}
```
