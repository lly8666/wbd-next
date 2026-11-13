# PLAN029 H1753｜WinGo原生COM已编译，真实Windows Defender单规则OS回读门

- H1752 SOURCE `61cb246f309439538652e9ab9bb98d445e6a433d` [Action43436316554](https://github.com/lly8666/wbd-next/actions/runs/43436316554) **SUCCESS_SCOPED**：原 Go Windows装配、native COM代码编译、Defender owner intent/owned/CAS故障注入测试通过。H1751原Win编译FAIL保留。
- 纯Backend mock不证明Win32 Defender COM具有可调用权限/正确枚举。本批在原H1661 Windows2025单SOURCE编译完成后，同一短暂runner、显式`WBD_PLAN029_REAL_DEFENDER_TEST=1`且`GITHUB_ACTIONS=true`才运行**一个**真实`INetFwPolicy2`单规则Add→逐项回读→checksum owned WAL→精确CAS Remove→读回OS与WAL双缺席。
- 测试规则仅指定未分配的本地10.234.12.34、remote198.19.87.99、TCP端口45321，随机每代规则名。不监听socket、不全局disable、防火墙profile不更改、无旧WFP。任何无法确认规则移除都FAIL并保留WAL以便人工处理；没有伪造真实双出口。
- 当前源码H1753真实Windows OS测试PENDING；即便PASS仍不能声称原Go产品TCP postApply已经ENABLE，D1-D5/P1-P2/padding/GUI仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Preserve H1752 Windows Go COM compile and Defender WAL mock pass, add explicit ephemeral Windows native one-rule Defender OS Add/readback/CAS cleanup test; no product TCP enable"}
```
