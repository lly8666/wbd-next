# PLAN029 H2040｜将已完成的H2031真填充源实测登记到功能卡verification

- [H2031 原生Action43901130216](https://github.com/lly8666/wbd-next/actions/runs/43901130216) 已由H2036归档 `docs/evidence/M0/PLAN029-H2036-H2031-REAL-STARTUP-PADDING-MTU-20261117.json`，当前功能卡`summary`已写PASS_SCOPED，但`verification`末尾仍只有旧H2025 PLANNED，容易在收口时误认为全新20..30条/2..3s策略未测。
- 本次仅追加一条精确源`b76240bedb04237780bd13377bfe7aae38785018`的`FUNCTIONAL_PASS`：Windows/Linux真Npcap接纳31 record/6579B，真实WSL2 eth0 41条完整TLS样式密文record长度71–589B，外层IPv4最大707小于当次1400MTU，双向TCP/UDP和owned Stop通过；密文不直接证明逐条pad字节，窗口/独立0..500靠同源Rust单测约束。旧历史PLANNED记录未删除。
- 无产品/测试夹具改动、无新Windows Action派发、无Game4结论升级。H2038 真Game4 [Action43942345347](https://github.com/lly8666/wbd-next/actions/runs/43942345347) 仍按源锁原生收件；H2039 G2 direct evidence source 修复后 [治理Action43942635935](https://github.com/lly8666/wbd-next/actions/runs/43942635935) SUCCESS。
```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"H2040 registers already archived H2031 true physical pcap and both owned Stop in feature verification without product edits or false per-record packet inference."}
```
