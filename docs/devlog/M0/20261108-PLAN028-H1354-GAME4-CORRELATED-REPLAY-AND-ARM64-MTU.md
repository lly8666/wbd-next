# PLAN028 H1354 — 原始 H1353 CI FAIL 离线重算；ARM64 附带场景单列

## 根因与处置

H1353 [原始原生网测](https://github.com/lly8666/wbd-next/actions/runs/42435004151) 确实**FAIL**，仅在最后报表 `assert len(sent)==len(got)==18000` 处抛错。原始 Go/TLS+Rust 真实五客户端业务已执行180秒、随后的10秒 drain、owned Stop、原始38文件ZIP上传；真实10ms app 数组包含 inclusive 端点共 **19001** 桶。原错误应修报表而不是重复180秒网测或掩盖原失败。离线副本脚本 `tools/m0-plan028-h1354-offline-h1353-replay.py` 限定 **19001** 并保留其余业务、租约、Stop、物理 qdisc 断言，不修改原 H1353 脚本和网络产物。仅下载原ZIP的 [H1354 离线 Action](https://github.com/lly8666/wbd-next/actions/runs/42435645489) **SUCCESS**；原 CI FAIL 永远留在原 run。原ZIP SHA256 `d36bda92c7428fc80f2d98671fe1cb0ed7f61190c3c5bfcc405a9a9e8d02e65b` / 38文件 CRC PASS；离线产物ZIP SHA256 `b46baab01970b8f08b09c4fd8d5a0217660165f67e913148594e22ab8766984e` / CRC PASS。

## 原始网络限定事实

- x86 VM 四个逻辑vCPU、同一 443 真实原始 Go TLS、五个真实用户TUN+原始 Rust M4 ISA-L；产品二进制 SOURCE `6c5fd909b9f42d1af89c698cdaabc79bbb72e589`，场景 wrapper `104a5213c10e4869f948069071d8af4311403e91`；无产品热路径改动，所有发生器 `capacity_exceeded=false`、无 app error。
- app实际持续180秒，两方向总体峰值目标各10Mbps、独立损伤为0%、Dave Game4 固定最高档单程150ms。t=**70.017s** 在 Dave 所有四lane共用的**同一真实veth** 双向 netem 强制100%丢包，t=**78.029s** 恢复；恢复前真实 tc qdisc uplink/downlink drops **26,653 / 26,657**。这证明共同底层断路，**不声称多个独立物理lane路径**。
- t=72..76s Dave业务实际上行及下行各发送 **1,050,112B**、各收0；老原始 rapid report 所见活跃发送无收件8010/8000ms是**预期100%黑洞，不得冒称健康阶段PASS**。恢复后两向原始业务首次收件各 **141ms**，t=82..102s UDP交付比均 **0.99691**，晚期两向无业务无收件空洞（同一宿主单调钟10ms桶；不跨设备推时钟）。
- Alice/Bob/Carol/Erin 在 Game4 黑洞窗口 t=72..76s 仍均持续两方向 UDP，双方向各10ms桶测得最大活跃无收件空洞 **0ms**；五客户端最终 exact owned Stop、服务器共享TUN Stop 全部可观测，五租约 `pending_overflow=0` 且 offered=delivered；静态测试专用真实veth MAC 10/10 PERMANENT 在始末一致。宿主各阶段平均busy7.31/11.21/15.64/11.89%，不能据此归因产品CPU。
- 原报表 `rotation_continuity_not_proven` 五条照留：600s计时器在180s内**NOT_TRIGGERED**；从未声称 L1 七模式二次轮换。判读：**L2 本一条相关共同底层双向黑洞及真实恢复 + 健康兄弟隔离 PASS_SCOPED；原CI FAIL（报表）、原黑洞业务断流、历史 H998/H1317 FAIL 都保留**。详见 [H1354证据](../evidence/M0/PLAN028-H1354-H1353-X86-CORRELATED-GAME4-RAW-REPLAY-SCOPED-PASS-20261108.json)。

## 附带 ARM64，独立资格

共享 H1259 夹具命中旧 ARM [H1291 workflow](https://github.com/lly8666/wbd-next/actions/runs/42435004153) 的 `push.paths`，故**自动额外触发**，不是手工重复dispatch；原生 aarch64 双端 build和scene均PASS，180s真实五客户端 baseline 无alerts。Alice 同NIC/IPv4 真实物理veth两端MTU在业务 t=70.024s 从1500→1280，实际新TLS/native M4 generation与server确认port、旧代精确Stop有证据，最终Alice第3分钟双向各约6.4Mbps接近完整交付；不能借此改写 H998 原socket 缩窄失败，也不能当Win/物理入口或所有七模式覆盖。见[ARM64证据](../evidence/M0/PLAN028-H1354-INCIDENTAL-ARM64-REAL-MTU-1500-1280-SCOPED-PASS-20261108.json)。

## 剩余

PLAN028仍 **IN_PROGRESS**。待依专项验收逐项收 L0确定性owner、L1七模式每种两个真交接/Windows真独立设备驱动与通知、L2其他单/双向黑洞与正常100–200Mbps容量和退化边界、冻结SOURCE后代表性双1800s。Android、真实物理、旧同socket FAIL等保持单列。后续029/030不动。
