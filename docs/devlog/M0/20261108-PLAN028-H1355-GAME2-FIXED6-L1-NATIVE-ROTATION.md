# PLAN028 H1355 — 最新冻结二进制 Game2 Fixed6 的真实 L1 双交接（待收）

- **状态：IN_PROGRESS / NOT_YET_VERIFIED**；前次 H1354 scoped L2 PASS 与原 H1353 CI FAIL 严格分开。新 [H1355 Action](https://github.com/lly8666/wbd-next/actions/runs/42436151532) preflight job128595305591 PASS，真实业务 job128595332447 等候结果；不重复 dispatch。
- 原始完整 Go TLS 443 / Rust M4 native ISA-L 二进制 SOURCE `6c5fd909b9f42d1af89c698cdaabc79bbb72e589`，复用旧 H1286 x86 一次性 manifest、ELF62、三文件hash；场景代码 wrapper `0f1aea9ca1dbf868860d9daf01aa480f75c82d17`；**没动产品、record、FEC内核、共享TUN、握手或封装**。
- 一 Action 一场景：五个真独立客户端 Alice Normal Off、Bob Auto、Carol Game2 **Fixed6**（旧近例是Off）、Dave Game4 Fixed6（保留原有末尾 FEC native backend readback）、Erin Normal Fixed6。各方向原始 base4/4/3/6/3Mbps，在四阶段 .2/.35/.5/.35，峰值合计10Mbps/方向；物理veth双方损伤0%、单程延迟0/10/20/30/0ms，测试专用真实 ARP 10/10 PERMANENT。真实UDP双向，Alice/Bob同时真实 framed TCP；不做流量应用重试。
- 已实证 H1295 ARM64 180s 97/101/103/89/107s interval + 5s jitter 全五客户端至少两次真实 TLS/Rust M4 rotation/selected Game4 lane hot swap。本 x86 固定了相同 timer 配置、保持单调钟但**必须重新读回**所有 owner：Normal/Game2应至少3次成功 generation（两个旧 exact Stop），Game4应至少两条不同 lane 热换并有server确认；不能只按 timer elapsed 通过。
- 申请根由：H1230 全七模式×四代确实曾在旧 SOURCE0cda有资格；当前相同产品配置未全部在冻结 SOURCE6c5 回归，Game2 Fixed6 是一个小而可区分的真实分支缺口。低负载避开容量假象，不把 Game4 Off 一并塞到这个对FEC stop诊断固定绑定的公共夹具而造成假失败。
- 完整 L1/Windows、L2更广黑洞及容量、L3两场1800s依旧待验，feature总体仍 `experimental`，PLAN028未完成。结果沿 cursor 收档。


## H1355 native original result（已实测）及 H1356 报表离线收口

- [H1355 native Action](https://github.com/lly8666/wbd-next/actions/runs/42436151532) **SUCCESS**：x86_64双方原生 Go TLS443 / Rust M4，产品 SOURCE `6c5fd909b9f42d1af89c698cdaabc79bbb72e589` 的三 ELF SHA/manifest 实际核对、五租约原始TUN双方、真实180s容量内压力场景。原ZIP [artifact13599652010](https://github.com/lly8666/wbd-next/actions/runs/42436151532/artifacts/13599652010)，SHA256 `6ce2aad2c82071d63aaef12f0acbea613d634389a23799ddf0d6aa8a1b5433e5`，36文件CRC PASS。
- 四位普通和Game2 owner（Alice/Bob/Carol/Erin）各实际完成客户端及服务端确认的 generation **1→2→3**，旧代 exact Stop **1→2**；Dave Game4 Fixed6 在原始group内热换 **lane1、lane2** 两个独立lane，两次服务端M4原始tuple确认；其余健康lane未整组退役。Carl Game2 **Fixed6** 的client+server readback均出现，区别旧 Off-only 证据。
- 真正的双向10ms UDP 原始业务：Alice 1/1；Bob .99993/.99993；Carol .99989/.99988；Dave .99983/.99983；Erin 1/1（上/下行交付率）。所有10ms活跃发送无收件最长 **≤30ms**。Alice/Bob 真实 framed TCP 各每向 7877/7877，四组无待发。五租约各 `pending_overflow=0` 且 offered=direct_delivered；所有五client与server确切最终 owned Stop；未达宿主/发生器容量告警。
- **保留原始通用报表警告**：H1286通用 `outer_counts(log,mode)` 将 Game2 Fixed6 的 STOP 误用 Game2 Off 标志读取，记录 `Carol NO_REAL_OUTER_COUNTER` 一条 `ALERTS_PRESENT`，但真实 Carol 有3条 `WBD_GAME_FEC_LINUX_NORMAL_OUTER_STOP`，首次保护record字节151249568、外观重复record字节884186、外观copy=1035。此为 **测量选择器缺口，不是数据面丢失**。
- 初次 H1356 **离线** Action [42436664955](https://github.com/lly8666/wbd-next/actions/runs/42436664955) 因老通用分析整体重算需要未入36文件ZIP的 `h1250-qdisc-after.txt` 而 FAIL；真实原始报表和网测均没缺此计数，不能凭空造qdisc文件或重测网络。H1356改为只读原始完整36文件归档中的Carol真实FEC STOP并仅修与外层counter相关的派生字段，其他原生业务、其他四client、轮换字段完全保留；[H1356离线 Action](https://github.com/lly8666/wbd-next/actions/runs/42436971713) **SUCCESS**，ZIP artifact13600460132 SHA256 `2246afcfeea3d5e9e76333b27210670aca807320c30cba406b5a4ae48c4976c8` CRC PASS。纠正五人首次外层protected record总计829077583B、外观已接受重复2624466B（`R/(F+R)=0.31555%`，不含控制C）。真实Carol FEC source30255、parity57007、native quanta3502、scalar23250、recovered_candidate0；不能用外观重复解释FEC或包损失。
- 同期原先治理因 cursor evidence_refs 把 ARM SOURCE104a 与 x86 SOURCE6c5 混写且x86证据未写顶层source_sha而FAIL，已修证据标签和source引用，治理在 [fc5c7f26](https://github.com/lly8666/wbd-next/commit/fc5c7f26f6ec0956a4ccd671d0bcbe69f478526b) **SUCCESS**，原失败不删。
- 归档： [H1355 L1 evidence](../evidence/M0/PLAN028-H1355-SOURCE6C5-X86-GAME2-FIXED6-REAL-ROTATION-SCOPED-PASS-20261108.json)、[H1356 original reporter evidence](../evidence/M0/PLAN028-H1356-H1355-SOURCE6C5-ORIGINAL-FEC6-OUTER-COUNTERS-OFFLINE-PASS-20261108.json)。**本 SOURCE 的 Game4 Off / 全七模式同源码仍缺；Windows真实双Npcap/Wintun、L2 Normal高于安全阶、L3两场1800s均未完成。PLAN028 IN_PROGRESS，不自称完成。**

```feature-impact
{"kind":"updated","ids":["original-lane-rotation-jitter","game-lanes","linux-raw-tun"],"reason":"H1355 frozen x86 original TLS/Rust authentic five-client Game2 Fixed6 2+ owner turnovers with real UDP/TCP and final exact Stop; H1356 real three-generation FEC outer counter offline replay corrected false H1286 Off-only marker without modifying native business or hiding original alert."}
```
