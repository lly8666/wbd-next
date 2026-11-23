# M0 H2335 · 2026-11-23 Game 外层表演式重传低 CPU 索引与双向实际证据

## 前一版真实 SOURCE 的限定结论
- main `60a20196d9c028c20d989232b991a6a0becb30e0`：Windows签名 Game2/Game4 OFF/fixed6 ×0/5/30% [12/12 jobs](https://github.com/lly8666/wbd-next/actions/runs/45130747250)；Linux原GoTLS+Rust客户端及服务端各自双向 Normal六档与Game2/Game4 OFF/fixed6三档 [18/18 jobs](https://github.com/lly8666/wbd-next/actions/runs/45130747501)。均为真实原生TUN/netem和Stop的 **scoped** 证据，不证明Windows服务端/Linux客户端互连、物理WAN或P1/P2容量。
- 30% Windows→Linux: Game2、Game4、Game2+FEC、Game4+FEC Windows侧均有1个真实外观copy，Linux服务端分别2/5/2/4。Linux端真实原F/R分别162584174/2550B（R/F=0.001568%）、325125028/4991B（0.001535%）、382125890/214B（0.000056%）、749091857/496B（0.000066%）。Windows Game每lane汇总F分母尚未读出，**不能写Windows Game R/F通过**。Linux客户端↔Linux服务端相同mode 30%仅各2/4/2/4次，原报告明确wire R/F未测；与Normal 30%约9%的外观强度仍有数量级差异，虽已比旧0%无条件洪泛安全。
- 同 Windows VM Normal 30% OFF→ON 的 [CPU pair](https://github.com/lly8666/wbd-next/actions/runs/45114832097)：进程4.7812s→5.3438s，增加0.5626s（占ON总CPU10.528%），真实双端Stop同一EXE/DLL；仅一次顺序测量不能归因可选重传算法成本。

## H2335 可审计的最小改动
- Linux Game旧路径即使唯一 `pending` 已占，也每隔一个首发DATA插 `OuterAckIndex` BTree节点，浪费CPU且没有新冻结copy资格。现在仅当**实际可保留的1/2抽样原密文**存在空槽、在lane冷却之外、长度合规时建1个索引；其余原DATA只以 O(1) `advance_untracked` 推进严格连续原TCP Seq，全部首发F仍逐包累计，不建Arc/树。新增64个真实firstcopy、仅一个index候选确定性单元。
- Windows Game OFF原本几乎每原DATA都索引，fixed6也在被本地shadow容量/采样/全局资格拒绝后留下孤儿索引。现在OFF和fixed6均同Normal采样1/2，且任何可选 `win_v3_admit_shadow`、缓存容量判断都早于BTree插入；原首发F无条件进入预算，不影响业务/FEC。
- 绝不恢复旧逐record M2 Receipt，不改变真实认证ACK≥1s、每ACK阶段一次、每PN/原密文一次、80ms lane pacing、R/F10%上限、FEC parity分离、无损防洪泛、默认ON。**新SOURCE这两处产品改动无任何测试PASS可继承**；已同步原生测试和Windows12/Linux18现网矩阵触发，必须重取同SOURCE结果。仍缺Linux客户端→Windows服务端真实互连与Game ON/OFF同VM CPU差值。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Game Linux indexes only the one admitted sampled original frozen appearance candidate; Windows OFF/fixed6 share Normal half-sample and reject inadmissible snapshots before allocating ACK BTree nodes; firstcopy F unchanged and no policy/default/limit change; native source qualification pending."}
```
