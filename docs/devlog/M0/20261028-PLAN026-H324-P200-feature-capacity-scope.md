# M0 PLAN026 H324｜产品能力卡记录P200源锁容量受限（2026-10-28）

源锁 `0d09cd5e` Action40651485360 双向kernel TC 200ms/250Mbit/s/30%完整60s真实运行：Normal/off有真实首到、UDP/TCP和owned Stop，但发生器实际148.0198/108.1181Mbps，均不达225Mbps输入门，因此产品卡记为 **CAPACITY_LIMITED**，不是FUNCTIONAL_FAIL或250Mbps PASS。对应收据已在 `docs/evidence/M0/PLAN026-P200-source0d09-Windows-Linux-capacity-limited-20261028.json`，原源 `055026fd`、`f93f7fe7` 的双向真实功能PASS保留。

修复了测试发生器固定800us sleep和每个UDP包重分配后，下一轮精确SOURCE `c8352931` 已触发新的P200，不能用新的工况结果倒填旧SOURCE。

```feature-impact
{"kind":"updated","ids":["normal-off","windows-native-transport"],"reason":"将真实已完成的SOURCE0d09 P200 250Mbps压力首测标为CAPACITY_LIMITED，明确250Mbps生成负载未达、首到和Stop成功；保留旧功能PASS并禁止互相继承。"}
```
