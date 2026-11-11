# PLAN028 H1617｜原构件复用的两项原生闭环实证与七模式范围核账

测试Harness `cf03ab6b59b63c5f7b247a81826bc465fec6947f` / Game2 Harness `9148b784`；正式产品二进制仍是 `8a31375e36bb6a93860c5579e64b4a39d0b6e346` H1600 成功Action`43027983611` 的原Go credential TLS443/FakeTCP＋Rust native ISA-L三件。新Harness对 `crates/r0/Cargo/prepare_windows_wiring` 和原本Linux netns fixture产品调用路径diff=0，两个独立Runner两条独立Action、没有任何Go/Rust重新编译。具体独立二进制和ZIP文件 SHA256、原始失败记录见 [H1617 evidence](../../evidence/M0/PLAN028-H1617-SOURCECF03-PREBUILT-NORMAL-FAILED-B-A-LIVE-GAME2-OFF-20261112.json)。

**Game2 Off Auto / 真实物理源与MTU切换**：[Action43061710360](https://github.com/lly8666/wbd-next/actions/runs/43061710360) overall SUCCESS；artifact`13874290798` ZIPsha`eca91b8eefa411113522e23e08908bf3da4167f12886723779e12b8c5432aa86`。原TLS 4个独立ClientHello (两代各2lane，source `.2`/ `.3`各两tuple)，原Rust M4新组认证后A+B→B、OS物理MTU1280→inner TUN1193，切前5、切后5次真Linux TUN UDP回声，原始客户端+共享服务端Stop。旧Game4 `remaining_flows=4`测试断言在临时生成的Game2脚本准确换为2，未改原产品或硬门。**PASS_SCOPED Linux x86 native Game2 Off**，原错误断言Action`43060138947` FAIL保留。

**Normal Off / 同物理出口候选B失败时A仍活＋B3恢复**：[Action43062378203](https://github.com/lly8666/wbd-next/actions/runs/43062378203) overall SUCCESS，artifact`13874281596` ZIPsha`9043c81357df699d77590e16f30d524b1ae4e1f9ec1421ad452d42d1da734fb2`。本场没有物理IP或MTU变化：源`10.25.0.2`、物理1500，原外层用户配置仍1460。仅此场显式`--rotation-interval 30s`（产品默认0）开启原Go冷轮换，内核仅禁止候选来源端口B的原TCP443，真TCP drop1，原Go `candidate_failed generation2 old_untouched=true`，在严格阻断期间由未Stop的A发送并收到一个新的真实内核UDP回声，且原Go客户端/服务端进程存活。解禁后原Go TLS＋Rust新B3来源端口64791完成受保护M4 READY，原A在**16872ms** grace后精确 Stop，随后B3 5次全新UDP收到5/5，最后client/server原生Stop。**PASS_SCOPED Linux x86同物理A保留硬门**；不外推到物理旧A出口确实不可达的场景。旧原H1614变物理IP/MTU导致A UDP没回、H1615 5s触发B4导致最后UDP超时两条Action仍FAIL留档，不能用新范围自动消除原缺陷。

**七模式与测试效率**：原旧`0cda9157` Action`41970545107`严格原生Linux x86七模式短真实网络，28次新组冷切换、16220次投递、16219收到，有1个Game2 Off未交付；只属于原SOURCE。新SOURCE`8a31375e`已实证代表Normal Off/Auto、Game2 Off、Game4 Fixed6，并有Normal Fixed的Erin实运行（fixed强度上限在该证据中未读回）。Game2 Fixed6与Game4 Off的七模式旧SOURCE正向可按相关组件证据复用，但**不冒充当前二进制各自独立真网络PASS**。不为“矩阵齐整”重刷整套。Windows新认证后的idle/物理path尚缺稳定签名DUT与共享Linux业务；Windows独立DUT 1800s L3和600s压力尚未达完场条件。近innerMTU用户明确跳过；同宿主双Wintun不跑，旧失败保留。028继续`IN_PROGRESS`。

```feature-impact
{"kind":"updated","ids":["original-lane-rotation-jitter"],"reason":"Add exact current original-Go/Rust prebuilt single-physical candidate-B failure old-A live then B3 authenticated real UDP/Stop, and source-scoped Game2 Off evidence; do not change defaults or protocol."}
```
