# PLAN027 H399｜修复 H398 cursor 引用上限
2026-10-30。[H398 governance40945596235](https://github.com/lly8666/wbd-next/actions/runs/40945596235) 两个 job FAIL，明确首错 `SCOPE_AUDIT_FAILED: unbounded context_refs`；H398 新增证据热引用使 cursor 由8变9，超过 `tools/governance.py` 的8条硬上限。移除已归档 H374 的**热引用**，原 devlog 不删，保留当前 PLAN027、H395/H398 精确证据，cursor 维持8条。无产品代码变更；H396 native 91/134/114 等真实 PASS 不受该治理失败影响，H398 FAIL 保留。
下一步取本次自动治理结果；继续双方线上低频 Quality/ACK/Receipt 退役，A/B/C 仍 NOT_RUN。

```feature-impact
{"kind":"none","reason":"Only cursor bounded-reference repair and governance failure accounting; no product behavior, parameters, or feature verification changed."}
```
