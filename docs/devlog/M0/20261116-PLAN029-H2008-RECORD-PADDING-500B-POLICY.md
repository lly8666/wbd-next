# PLAN029 H2008｜仅调整 Tunnel 启动填充候选 0..500B，不突破真实预算

- 用户收口前授权将**每业务record随机候选上界从256B提高到500B，含0**。原单record `MAX_RECORD_PAD` Rust常数从256改为500；随机 `n=PRNG%(min(500,wire_room,remaining_flow_budget,business_10pct)+1)`，不会生成不可能的>MTU payload，也不会等待增大填充空间。默认off、Direct无填充、12条/每流2KiB/256跟踪/1–2s窗口仍原有，Game4/Fixed未配置安全填充仍不暗中开启。
- 原H1799 Windows/WSL2 M1 NPF实际16条/50B padded record 的旧SOURCE真实Stop PASS；**不是500B新来源实测**。新增纯Rust普通1228B IPv4 UDP业务样本（含1200B payload）×64确定性种子：可找到>256B候选、每次≤500B及实际room273，每流≤2048、≤12×1200/10、12条后不再填。单测试不占真实Wintun/NPF回执。
- 方案§4旧256B同步改为500B。仅在独立Native Padding Normal Tunnel受控原SOURCE一次实测中检查真实业务、NPF接纳padding字节、有效MTU/Stop。先收来源锁定Action，编译或功能PASS不能冒充随机上限/CPU增益；所有旧D1–D5/P1–P2缺口保留。
```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"H2008 increase only random startup Tunnel record padding candidate maximum from 256B to 500B while retaining verified MTU, budget, 12-record/2KiB/cap, default off and Direct unchanged."}
```
