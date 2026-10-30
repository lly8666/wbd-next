# PLAN027 H453｜H452 Action 红项的最小回归修补

SOURCE cdef278f：native-functional run40991692192 recovery 96 PASS/2 FAIL。新增8MTU真实平滑已把同一tick第九stage0正确拒绝，旧单测却仍要Accepted；新单测跨100ms重复使用过期候选且把后续fresh事件时钟倒退。修正两个断言，保留真实平滑与时钟约束，不退回代码旁路。

Windows↔Linux run40991692231 cheap check 在启动真双端前因 assembly blob mismatch 停机。Go策略和其测试已更改，但manifest-plan020-m0.json保留旧blob；将两项result_blob更新为当前Git对象sha 4b1a9076/aada7132，保持原wobuzhidao SOURCE未动。

H452受影响Action红项不删；H453新SOURCE native/Win preflight/真双端尚无通过，PLAN027 A/B/C/长测继续。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct two exact CI test assumptions and frozen assembly source blob references; product behavior unchanged."}
```
