# PLAN028 H1489｜同一真实x86 Game2双物理交接两份原始ZIP业务全PASS，旧Action报表FAIL保留

从 `222a03eb53064771620e5821d82478969f8ee93b`、M0 H1488及当前Actions续跑：原H1488 [Action42638378892](https://github.com/lly8666/wbd-next/actions/runs/42638378892) 复用SOURCE `57b0d0c` 三原生ELF、ZIP artifact13684650590 CRC_PASS SHA `0f004276205331efd7165bcfb893bf649b20421370df99c340e29d44faddbd68`；被历史fixture push监控意外同时触发的H1200 [Action42638378870](https://github.com/lly8666/wbd-next/actions/runs/42638378870) 对当前源码构建第二份三ELF，artifact13684297738 CRC_PASS SHA `c2837a8d3334f2596256ec3df67228d6ff7ec43672e5804eb6aa9d2d64dca7e6`。两份manifest的原生 Go client/server+Rust .so 各 SHA256 **完全一致**，都是native x86双端真实TLS/RAW/TUN。

独立读两份原ZIP（不是stdout末行）原native shell均已经输出 `M0_PLAN028_H1199_X86_GAME2_FIXED6_TWO_PHYSICAL_HEALTHY_SIBLINGS_PASS` + `M0_PLAN028_H1151_X86_ORIGINAL_TLS_ONE443_NORMAL_GAME2_GAME4_FEC6_48_REAL_UDP_EXACT_STOP_PASS`；真实Gen1→2→3、旧1/2 owned Stop、Game2新代UDP 16+16、两个窗口各Game4/Normal 80+80回声成功、外层物理IPv4 `.2→.9→.2` / MTU `1500→1280→1500`、内层TUN `1358→1178→1178`、不改其他client、单443、全原生Stop。原source57b报告到旧Stop时间19.915s/10.986s，重构建同二进制19.677s/18.659s；包含故意10–20s RX退休宽限，**不等于握手/首业务SLA**。新80×400ms监视窗满足旧代回收。

两个原Action均标FAIL，**不是产品FAIL**：H1488外层Python `scope` 少了真实输出固定后缀 `_WITH_GAME4_AND_NORMAL_HEALTHY`；H1200原外层Python仍把真实80+80误期望为24+24。两者外层在原生完整PASS后才触发，原FAIL/产物保留，不能改原Action结论。离线严格ZIP SHA/CRC/manifest/生成夹具git blob/真实业务与Stop复审后仅定 `PASS_SCOPED`。小报表错误不为它重新测网。两个历史native workflow都切为手动dispatch入口，并修正报表条件，防止再因夹具push双跑；新增唯一H1489原ZIP纯离线review工作流，执行时无网络场景/无Go/Rust重编译。

H1484 ARM真实五client180s零损、H1485 Game4原生五回声合格资格仍复用；600s 75Mbps与1800s Alice 原FAIL、Windows L3、H998及物理/Android等PLAN028开放项不改写。PLAN028 `IN_PROGRESS`。

```feature-impact
{"kind":"none","ids":[],"reason":"Original native immutable ZIP offline evidence and two outer reporter-only fixes; no product, protocol or fixture-time change."}
```
