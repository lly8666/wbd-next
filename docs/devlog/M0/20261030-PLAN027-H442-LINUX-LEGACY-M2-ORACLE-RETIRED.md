# PLAN027 H442｜Linux 原生旧 M2 断言不再冒充替代逻辑

H440 Action[40985294022](https://github.com/lly8666/wbd-next/actions/runs/40985294022) Artifact12946287909：真实 original Go TLS 与 Linux Rust raw/TUN 已 C2S=8、S2C=8，Stop/读回其他单测PASS；仅旧WBC4逐record report检查 `AuthenticatedReverseReports=1,Covered2s=8` 未出现而 FAIL。H440 [40985293746](https://github.com/lly8666/wbd-next/actions/runs/40985293746)/[40985293776](https://github.com/lly8666/wbd-next/actions/runs/40985293776) 同理失败于历史releaseClient实际kernel M2确认。本次改回归oracle为真实应用/首发/RS恢复、旧高频Receipt零接受、Fixed/Auto不得借不存在的旧M2伪造Applied、双Stop清理；旧独立probe的旧Receipt编码和反例不动。

**真实阻塞仍在：Fixed/Auto新确认Applied替代凭证尚未接线，此次只把过时测试从正例改成不得虚报的负例，功能不算完成。** 新Action可确认测试是否真正重新通过；尚无A2-A5、B或C新源PASS。旧失败原文和Artifact保留。

```feature-impact
{"kind":"none","ids":[],"reason":"Only Go Linux old protocol regression expectations and workflow verification labels changed; product capability remains pending native qualification."}
```
