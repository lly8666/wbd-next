# PLAN027 H462｜恢复H461真迹并定位未决Auto发送错误

H461 Auto Action40998035077/artifact12951904475：Windows UDP384/0、Linux99/25；Linux 500ms原生M4聚合在40s记录32621976次error、FEC首发10/已拷9、parity计划9/实际0。H459的CLOSE计时器更改不能解决，不能归咎于缺统计成熟。

H461 C10 Action40998037302/artifact12952331677：10Mbps/25ms/0% 双向实际首到Windows99.999%、Linux100%；随后Linux重启超时10s且Stop NOT_RUN。新H461夹具start-linux.sh误写`echo $`（zip的PID文件仅2B），恢复`echo $$`并加单元回归。整体仍FAIL，不能由前段UDP美化。

复用现有opt-in `WBD_FEC_EGRESS_DIAG=1` 500ms采样，只增加FEC queued/open/staged/失败原因、native错误代码分布/tx链，无额外逐包输出。以真正同SOURCE Win/Linux构建和一次Auto真双端复验定位热错根因，不盲改FEC分组或认证、MTU、真实驱动。旧所有run/artifact/失败保留。A4/A5、B生命周期、C梯度和5分钟仍待推进。

```feature-impact
{"kind":"none","ids":[],"reason":"Test harness owned PID fix and existing opt-in low-rate native diagnostic enrichment; protocol/product default unchanged."}
```
