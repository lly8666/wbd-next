# PLAN028 H1355 — 最新冻结二进制 Game2 Fixed6 的真实 L1 双交接（待收）

- **状态：IN_PROGRESS / NOT_YET_VERIFIED**；前次 H1354 scoped L2 PASS 与原 H1353 CI FAIL 严格分开。新 [H1355 Action](https://github.com/lly8666/wbd-next/actions/runs/42436151532) preflight job128595305591 PASS，真实业务 job128595332447 等候结果；不重复 dispatch。
- 原始完整 Go TLS 443 / Rust M4 native ISA-L 二进制 SOURCE `6c5fd909b9f42d1af89c698cdaabc79bbb72e589`，复用旧 H1286 x86 一次性 manifest、ELF62、三文件hash；场景代码 wrapper `0f1aea9ca1dbf868860d9daf01aa480f75c82d17`；**没动产品、record、FEC内核、共享TUN、握手或封装**。
- 一 Action 一场景：五个真独立客户端 Alice Normal Off、Bob Auto、Carol Game2 **Fixed6**（旧近例是Off）、Dave Game4 Fixed6（保留原有末尾 FEC native backend readback）、Erin Normal Fixed6。各方向原始 base4/4/3/6/3Mbps，在四阶段 .2/.35/.5/.35，峰值合计10Mbps/方向；物理veth双方损伤0%、单程延迟0/10/20/30/0ms，测试专用真实 ARP 10/10 PERMANENT。真实UDP双向，Alice/Bob同时真实 framed TCP；不做流量应用重试。
- 已实证 H1295 ARM64 180s 97/101/103/89/107s interval + 5s jitter 全五客户端至少两次真实 TLS/Rust M4 rotation/selected Game4 lane hot swap。本 x86 固定了相同 timer 配置、保持单调钟但**必须重新读回**所有 owner：Normal/Game2应至少3次成功 generation（两个旧 exact Stop），Game4应至少两条不同 lane 热换并有server确认；不能只按 timer elapsed 通过。
- 申请根由：H1230 全七模式×四代确实曾在旧 SOURCE0cda有资格；当前相同产品配置未全部在冻结 SOURCE6c5 回归，Game2 Fixed6 是一个小而可区分的真实分支缺口。低负载避开容量假象，不把 Game4 Off 一并塞到这个对FEC stop诊断固定绑定的公共夹具而造成假失败。
- 完整 L1/Windows、L2更广黑洞及容量、L3两场1800s依旧待验，feature总体仍 `experimental`，PLAN028未完成。结果沿 cursor 收档。
