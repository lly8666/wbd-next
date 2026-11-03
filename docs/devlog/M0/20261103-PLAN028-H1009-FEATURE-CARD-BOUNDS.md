# H1009｜PLAN028 Game单端口功能卡容量修复

SOURCE2072554的Governance job PASS，但Feature catalog因Game功能卡JSON超过16KiB容量限制而FAIL（Action 41576418478）。本次仅将该卡压缩为等价JSON、去除本次H1008与完整devlog重复的一句未测说明；全部历史verification证据行、当前未验状态、代码引用与行为范围保留，产品SOURCE不动，不复派产品测试。

真实Game2/4单端口native建链/UDP/TCP/Stop只有本SOURCE对应实测Actions结束后才可推广。parallel Action 41576418458虽绿，其Game输出为`product=NOT_RUN`，不得算新SOURCE的真业务PASS。H998失败照旧。

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Preserve all Game verification rows and code refs while compacting JSON below 16KiB; no source/product qualification change."}
```
