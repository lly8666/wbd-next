# PLAN029｜解除循环验收门与分类压力处理

用户要求将审阅后的修订写入029与长期提示词。基于main `85131fbb7893abecd7422bb195f5efc9ca0a5012`，本次仅更新文档/导航，未修改产品、未dispatch、未新增产品PASS。

- 契约§3B：精确owned Defender Allow A/B/C及Block优先级，定位共同Wintun回注，不以未知根因永久阻断后端选择；UDP/OS事务独立推进。真实adapter可执行待验流程，不用assemblyOnly要求先PASS才可测；Ready仍据实际状态。保留认证/租约/generation/MTU/owned清理与Wintun生命周期。
- 契约§5：附件第八条资源约束改为分类退让。Direct4096软水位/16384默认硬限按需增长；TCP单流背压、UDP局部丢弃、DNS缓存淘汰/事务失败/FakeIP安全回收。FlowPin共用max可能误挡Tunnel是接线风险，未声称已确诊当前网络失败。64MiB为分配上限而非队列目标。
- D3/P2新增小容量压力验证，检查其他流/Tunnel继续及恢复；有限诊断、真实出口、代表性清理，不扩攻击或多代理矩阵。同步029正文、M0专项/通用提示、registry、cursor next_action和功能卡；不覆盖M0当前SOURCE/checkpoint/测试状态。

验证：本提交运行governance validate、feature catalog check和diff检查；网络实施与验收仍由M0继续，历史失败保留。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"User-approved PLAN029 bounded firewall/backend diagnosis, removal of circular execution gates, per-resource pressure isolation and targeted validation; design only, no product qualification change."}
```
