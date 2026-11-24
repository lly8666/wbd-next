# M0 H2335 · 2026-11-23 Game 外层表演式重传低 CPU 索引与双向实际证据

## 前一版真实 SOURCE 的限定结论
- main `60a20196d9c028c20d989232b991a6a0becb30e0`：Windows签名 Game2/Game4 OFF/fixed6 ×0/5/30% [12/12 jobs](https://github.com/lly8666/wbd-next/actions/runs/45130747250)；Linux原GoTLS+Rust客户端及服务端各自双向 Normal六档与Game2/Game4 OFF/fixed6三档 [18/18 jobs](https://github.com/lly8666/wbd-next/actions/runs/45130747501)。均为真实原生TUN/netem和Stop的 **scoped** 证据，不证明Windows服务端/Linux客户端互连、物理WAN或P1/P2容量。
- 30% Windows→Linux: Game2、Game4、Game2+FEC、Game4+FEC Windows侧均有1个真实外观copy，Linux服务端分别2/5/2/4。Linux端真实原F/R分别162584174/2550B（R/F=0.001568%）、325125028/4991B（0.001535%）、382125890/214B（0.000056%）、749091857/496B（0.000066%）。Windows Game每lane汇总F分母尚未读出，**不能写Windows Game R/F通过**。Linux客户端↔Linux服务端相同mode 30%仅各2/4/2/4次，原报告明确wire R/F未测；与Normal 30%约9%的外观强度仍有数量级差异，虽已比旧0%无条件洪泛安全。
- 同 Windows VM Normal 30% OFF→ON 的 [CPU pair](https://github.com/lly8666/wbd-next/actions/runs/45114832097)：进程4.7812s→5.3438s，增加0.5626s（占ON总CPU10.528%），真实双端Stop同一EXE/DLL；仅一次顺序测量不能归因可选重传算法成本。

## H2335 可审计的最小改动
- Linux Game旧路径即使唯一 `pending` 已占，也每隔一个首发DATA插 `OuterAckIndex` BTree节点，浪费CPU且没有新冻结copy资格。现在仅当**实际可保留的1/2抽样原密文**存在空槽、在lane冷却之外、长度合规时建1个索引；其余原DATA只以 O(1) `advance_untracked` 推进严格连续原TCP Seq，全部首发F仍逐包累计，不建Arc/树。新增64个真实firstcopy、仅一个index候选确定性单元。
- Windows Game OFF原本几乎每原DATA都索引，fixed6也在被本地shadow容量/采样/全局资格拒绝后留下孤儿索引。现在OFF和fixed6均同Normal采样1/2，且任何可选 `win_v3_admit_shadow`、缓存容量判断都早于BTree插入；原首发F无条件进入预算，不影响业务/FEC。
- 绝不恢复旧逐record M2 Receipt，不改变真实认证ACK≥1s、每ACK阶段一次、每PN/原密文一次、80ms lane pacing、R/F10%上限、FEC parity分离、无损防洪泛、默认ON。**新SOURCE这两处产品改动无任何测试PASS可继承**；已同步原生测试和Windows12/Linux18现网矩阵触发，必须重取同SOURCE结果。仍缺Linux客户端→Windows服务端真实互连与Game ON/OFF同VM CPU差值。


## H2336 · 新 SOURCE 完整 Linux 真网核收与同机 CPU 复测
- main 产品 SOURCE `dfdb388536ed3732260fcc9be7c503cd9bc21394` 的 [Linux 原 GoTLS/Rust client↔server 双向 18 场景](https://github.com/lly8666/wbd-next/actions/runs/45137388828)：**19/19 jobs PASS（1 二进制构建 + Normal 六档 + Game2/4 OFF/fixed6 各0/5/30%）**；所有真实 native netem、双 owned Stop、同源 SHA。旧 SOURCE `60a20196d9c028c20d989232b991a6a0becb30e0` 与本 SOURCE Game12原产物逐档比对，Game2 client/server各2、Game4各4次可选原密文复制，0/5/30均未变。即**没有候选丢失，但比例也没有随丢包增长**。真实 Game wire R/F 字节双端不齐，不应由复制包数估算。
- [真实 Linux Game2 30% 同一 runner OLD→NEW→NEW→OLD](https://github.com/lly8666/wbd-next/actions/runs/45138901381)，旧源码 `60a2019`、新源码 `dfdb388`，测试夹具 SOURCE `ef7e3c1b5e362d705056880b1c0f139ee54a9991`：4/4真实Linux GoTLS/Rust client/server、双向netem滴包读回、owned namespace完全清理、Stop、每端各2次外观均合格。客户端整进程CPU OLD=(1.99,2.01)均2.000秒，NEW=(2.01,2.01)均2.010秒，新-旧+0.010秒（+0.50%）；服务端 OLD=(2.08,2.11)均2.095秒，NEW=(2.11,2.11)均2.110秒，新-旧+0.015秒（+0.72%）。各次实际唯一首到约9.08–9.11 Mbps。**小样本 CPU 差值在计时/虚拟机波动范围，不能认定低CPU收益或显著退化；非算法独立采样。** 严格不以跨runner先前高损2.17→3.83秒比较宣称优化成败。停止类似微调，继续真实表演外观证据。
- 新 Windows签名 Game2/4 OFF/fixed6 12组矩阵 [#45137388745](https://github.com/lly8666/wbd-next/actions/runs/45137388745) 正在核收。Game4/5%某个 job 在 `git fetch` 已检出的同 SHA 时 GitHub HTTP403，**业务未开始、非产品重传失败**；旧成功不能继承，需待矩阵完成后只针对失败job重新运行。Windows Game原 F/R 统一字节总账依旧未测；Linux-client→Windows-server原生角色也不在当前构件范围。PR自身source未经新矩阵，因此目前只算 main 局部实际证据。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Game Linux indexes only the one admitted sampled original frozen appearance candidate; Windows OFF/fixed6 share Normal half-sample and reject inadmissible snapshots before allocating ACK BTree nodes; firstcopy F unchanged and no policy/default/limit change; native source qualification pending."}
```
