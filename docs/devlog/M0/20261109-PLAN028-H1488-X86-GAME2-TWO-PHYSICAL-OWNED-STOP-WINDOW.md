# PLAN028 H1488｜H1487 原ZIP离线PASS收件，x86 Game2双真实物理换路修过短的健康兄弟采样窗

最新main `a1e66eae5866ca1e1460afbc71c3fd1653972cea`，cursor H1486；H1487 [Action42634436099](https://github.com/lly8666/wbd-next/actions/runs/42634436099) 原artifact13681532478 ZIP source57b 纯离线审计已PASS，原H1485外报表Action FAIL保留，原五个 UDP echo 真PASS，无新网测。H1484 同source ARM64 五client180s 10方向零缺、Normal B6/Game2 B2真认证证明仍PASS_SCOPED。

独立H1200 [原x86 Action42630288227](https://github.com/lly8666/wbd-next/actions/runs/42630288227) artifact13681045719 记录首波Game4/Normal的24个原生双向单包UDP探针全部成功，已完成Game2服务端B authenticated Health/route两个新代证明；但继承ARM fixture在`new1` **等到** client Gen2 READY **和** old Gen1 EXACT Stop以后才计时，其断言却要求24×400ms=9.6s的监视窗口涵盖该完整过程。现行`originalLaneRetirementGrace()`恰有10–20s最小到最大旧代宽限，另加MTU/本地TLS、≤5s认证证明。因此原硬门在现行成功实现也可能数学不满足，不是证实产品失联。H1200 原FAIL保留、两次真实切换未验不能置PASS。

只修`tools/m0-plan028-x86-game2fixed6-two-physical-handover-fixture.py`生成的x86本场：首/次波监视改为80×0.4s=32s，覆盖5s B冷证明+最长20s旧代grace+7s调度裕量；2次共320健康兄弟实际UDP echo，另有旧初始36、Game2新业务32、其它Stop后的12及有限重试，fixture本地UDP服务accept上限360→640，不加新产品缓冲/发送。保持每个echo需完整真实payload响应，任何失败仍硬FAIL；Game2三代/两个old owned Stop/两次NIC源IP与MTU真实读回/lease/其他client不换代全保留。

新增单一H1488 x86原生独立Action，直接拿原 [Action42630288111 artifact13679959152](https://github.com/lly8666/wbd-next/actions/runs/42630288111) 的三份原native ELF `source57b0d0c`（immutable ZIP SHA `1228dbeea002869c1a9f94fa17324174e330f1a758bb3236ad4552079a23778a`），核三ELF哈希、原 donor、architecture和manifest；**不重新build、不dispatch相同网络场景**，真双端一VM、一个网络job，两次路径顺序测量。提交时场景 **NOT_RUN**；必须收原始 Action+artifact 后按触发/完整性判定。当前容量 H1461 75Mbps/1800及Windows L3仍OPEN，H998/Android/物理限制留存，PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Fixture timing correction for genuine x86 Game2 cold B vs 10-20s owned old Stop, and one source-locked missed real dual-physical scenario; no product/wire/config change."}
```
