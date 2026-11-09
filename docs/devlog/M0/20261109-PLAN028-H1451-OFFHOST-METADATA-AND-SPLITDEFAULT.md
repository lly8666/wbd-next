# PLAN028 H1451 — 独立Linux控制面观察与分半默认路由盲点

旧Windows原生Action42546907707 SOURCE724a最后用户业务720.2s正常，GitHub第19步仍in_progress，原始1800s/Stop缺。H1450防重复Action42550925082 CI成功、原生Windows L3 SKIPPED，治理42550925135 SUCCESS。Windows本机既是Github Runner也是Wintun DUT，不继续发同拓扑长测。

仓库原生恢复路径显式提到0.0.0.0/1和128.0.0.0/1。新增真实IPv4最长前缀语义的离线反例：物理0/0不变、旧GitHub service/32可走物理，新的公网service不在/32名单时会被Wintun/1覆盖；**并未得到原失联Windows当时的/1 OS快照**，不能声称已确定根因。必须独立DUT上调用Find-NetRoute按目标验证。

新增Linux-only只读监测 `.github/workflows/m0-plan028-independent-runner-forensic.yml`，严格锁定旧run+SOURCE，从独立Ubuntu actions查询job/step实际状态，独立落盘；不重跑也不cancel Windows、不改路由、不测业务。最多只能提供Github控制平面可见性，不是独立Windows DUT/Linux产品端。完整隔离A/B/C仍阻塞。028 IN_PROGRESS，H998旧FAIL，Android/物理NOT_RUN，ARM64和短测既有PASS_SCOPED保留。

```feature-impact
{"kind":"none","ids":[],"reason":"Only off-Windows read-only CI observation and deterministic IPv4 route-order counterexample; no product, protocol, MTU, FEC or OS writes."}
```
