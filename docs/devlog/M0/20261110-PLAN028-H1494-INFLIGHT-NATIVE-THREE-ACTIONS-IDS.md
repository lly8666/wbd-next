# PLAN028 H1494｜三项并行真ARM场景已启动，固定SOURCE/ISA-L预检全PASS

本轮从`44334db5d5a77e68b7d32f6149800a17dd5c83ec`回收 Actions，三个独立原生ARM64实例均真实通过同一source57b产物 artifact13679879171 ZIP CRC、三个ELF逐一SHA256和ISA-L/native后端/原donor核对：
- [H1491容量Action42660921771](https://github.com/lly8666/wbd-next/actions/runs/42660921771) job129311951242，50Mbps真实5-client180s → 宿主/产品与业务硬门允许才同VM顺序75Mbps180s，**IN_PROGRESS**。
- [H1492异构弱网Action42660921499](https://github.com/lly8666/wbd-next/actions/runs/42660921499) job129311949928，1800s，0/1/5/15/30%+0/15/50/100/125ms，**IN_PROGRESS**。
- [H1493健康低损Action42660921629](https://github.com/lly8666/wbd-next/actions/runs/42660921629) job129311951009，1800s，真实配置`WBD_PLAN028_30M_SCENE=baseline`即0/0/1/1/5%；GitHub `run-name` 旧“0–30%”文字只是元数据、不能误判场景，**IN_PROGRESS**。

现在仅三项产品SOURCE及架构/复用二进制预检PASS；尚无真实30分钟唯一交付/尾Stop结果，**不要写业务PASS**。H1491 75Mbps若50无余量按严格原因标`NOT_RUN/CAPACITY_LIMITED`，不是触发了的PASS。所有原source66fb600/1800 FAIL保留；H1484 ARM180s与x86换路限定资格复用。

Windows H1457早先600s Npcap/Wintun业务和两客户端Stop真实PASS，但其他SOURCE且非L3；历史托管Win1800因Runner/WSL2中断、无尾Stop，不能视为产品FAIL或通过。需要独立管理的Windows DUT/独立Linux peer才能真正合格，不能用Linux ARM替代、也不再无条件重复同托管长测。物理/Android仍NOT_RUN。PLAN028 IN_PROGRESS。
```feature-impact
{"kind":"none","ids":[],"reason":"Real started workflow receipt IDs and native SHA preflight observed; no code/fixture modifications or duplicate network actions."}
```
