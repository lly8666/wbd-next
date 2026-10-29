# PLAN027全任务绑定与提前收尾修正

用户反馈永久提示词使M0直接回复没任务，要求所有已授权任务做完才收尾。上一提交5d449bcb更新goal却保留旧PLAN026 assigned_task/cursor，提示词也可能将单阶段READY或容量止步误读为全局完成。

同步M0 assigned_task/cursor.task_id为R0-M0-PLAN027-FEEDBACK-AND-NETWORK-CLOSEOUT，active/partial/unverified。合并期间M0新增5088e88a/8a2a4dd9/ee6ff9e4及H374–H376恢复记录；全部保留其已恢复Actions/失败事实、checkpoint8a2a4dd9、last_tested_source302d和证据，sequence376→377仅记录本次完整派工绑定，不能重新要求恢复已收集的旧结果。权限、epoch、其他工位及其源码测试修复不变。

唯一收尾条件：产品替代实现→A简测→全部剩余B接线生命周期→C容量内矩阵/长测→必要修复回归/交付。完成单步自动推进，不等再派工；单族容量不足不免除其他事项；必要未跑/阻断/在途不能说没任务。同步提示词、START_HERE、AGENTS、project/registry/cursor及治理解释，复用有效旧证据，不新增框架或收紧数值指标。

仅文档/派工修正，无产品改动或测试dispatch，不向其他聊天发消息。静态治理/目录检查不冒充产品通过。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct active M0 assignment/cursor and whole-scope completion semantics only; no product behavior or recorded qualification results changed."}
```
