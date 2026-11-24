# M0 · 2026-11-22 Windows Normal 外层 ACK 机会保活（待验证）

## 源与最小改动
- main 产品提交 `dbd4a1121e843006055159b403b4a63838713f41`；PLAN029 实验分支对应同步提交 `217a2e3a77f9f64af0f6ab2698c8a70c267523fb`。两边源文件有不同原始 SHA，不能互称同构件。
- 原 `native_ack_only_due` 在本端持续有 TX 工作且未协商 SACK 时，抑制对端已经真实认证的累计 ACK 纯帧；“本端 active”并不能证明当前有反向 DATA 带上这个 ACK。Linux 端已经有按累计进展、10ms 合并的独立发法。这是可验证的反馈饥饿候选，不代表已确认历史全部机会修复缺失的根因。
- 修法只在累计 ACK 与最近实际发出的 ACK 不一致时提供 fallback；有繁忙本端工作时使用 worker 本地 10ms 最小间隔，静止无变化绝不发送，SACK 新真实缺口仍按原规则触发。原 ACK/PN、冻结密文、FEC、driver prefix、预算/Stop 和默认开关不改。不启动旧逐 record M2 Receipt。
- 增加原 Windows native-owner 单元真值表：busy 与未协商 SACK 有进展时等 10ms 后可发；未到 10ms 和无进展不发，已协商 SACK gap 不饥饿。

## 门槛与暂存状态
- **改动不是修复 PASS**：静态行为差异已审；当前本次产品源码的 native unit/真实 signed Windows↔Linux 0% 和 1/5/10/20/30% 尚待 exact SOURCE 结果。不能用旧原生证据继承。
- 0% 接近零 R；有真缺口、成本可承受时 R>0；持续充分负载的 R/F 上限约10%，原名义9%和 30% R/C 6% 属于历史高损资格，不是任意工况强制发包下限。每档单独记录双向实发 F/R/C、receiver unique bytes、P99、CPU/GiB、Stop 和受限容量，不因强行凑“表演比例”牺牲 fresh。
- 此外当前 PLAN029 PR68 5% 双组三腿中 b A′ relay UDP control 曾失联，不能沿用为有效双组性能 PASS。新重复测量只有在源码变化与可区别新证据时进行。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Bounded Windows native cumulative-ACK-only feedback fallback under busy local TX (10ms), preserving optional original-ciphertext once-only repair and existing budgets; exact-source native/network qualification still pending."}
```
