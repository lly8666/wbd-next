# PLAN027A H941｜用户指定一次手工跑剩余六场新默认 MTU 原生矩阵

恢复上轮 `a1362b22`：Windows↔Linux七模式真实联动 `41443311972` PASS，Win原生WAL `41443312219` PASS，ABI `41443312153` PASS；这些是旧默认1400夹具，不能作为新1460/1500实际合格。

H941先独立提交夹具 source `4d24565c343f9feb788574fbce22e6d1e9a73f36`（`[plan027a-h941-harness]` 禁止同次push不必要的旧1400原生整批），扩充唯一真实native selector：历史legacy1400、**不传用户MTU参数的产品默认1460**、显式1460/1500，并在真实Linux TUN authenticated Apply后核OS读回不超过outer。保留旧1280/1400向量，不改真实Go TLS、安全owner和密文。

本次只在新 `m0-plan027a-h941-one-shot.yml` 的明确commit marker `[plan027a-h941-once]` 和main SHA一致时，一次派发以下**六个独立Actions（不是把不同测试混成一种结论）**：默认1460七模式、显式1500七模式、1460 Normal 10M/25ms/0% 60s、1460 Game4FEC同基线、1460 Fixed 10M/250ms/30% 60s、1460 Game4FEC同弱网。工具使用现有 `workflow_dispatch` 真实签名驱动和确切SOURCE，逐场去重、结果/Stop/资源/first单独收。

当前仅编码与发起，实际结果不可预写PASS。两条30%常损不等于PLAN027A预声明5→30→5波形；旧内层DF0/DF1大UDP/IPv4 ICMP没有实测的原生注入，不准拿普通UDP/TCP的成功代替，无法因此宣布PLAN027A完整退出或开始028。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"User one-shot manual source-frozen native test batch for real implicit default outer1460, explicit1500 and scoped 1460 loss0/loss30; preserve historical 1280/1400 and record DF/ICMP gaps without false PASS."}
```
