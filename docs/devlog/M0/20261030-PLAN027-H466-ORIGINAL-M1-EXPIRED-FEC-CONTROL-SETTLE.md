# PLAN027 H466｜Auto原始Linux M1过期状态泄漏导致M4单核空转：根因与最小修复

独立Auto H464 Windows↔Linux真实Action41000372316 artifact12953171887，同源product 0daddf：Linux TX在第一次INVALID后`staged=7`永久不变，500ms内后续88264次BAD_STAGE，parity r规划7/复制仅1，FEC失败原因全部零；失败在业务smoke（Windows初收8，Linux初收0），不是容量测量。原M1 Fresh队列`max_age_ns=50_000_000`，parity encode完成后`drain_tx`可能合法地丢弃全部过期ready记录。旧`ready.is_empty()`立即Err(INVALID)跳过FEC staged PN/Health-M2草稿settle，下一轮`fec2_staged_pns`非空立即Err(BAD_STAGE)，形成自锁和CPU饥饿。不是靠调低质量计时器解决。

Linux original owner变更：只有ready过期为空时保留同步M4完成/NotSent结算流程；不调用空sendmmsg，`classify_tx_turn(None,0,..)`明确failed、零copied；对全部staged parity记录按真实ready PN确认not-sent、调用原`settle_staged`释放/不重封，不引入新PN或重试。仅当实际M4 ready最后PN匹配反馈，才把末尾计作M2 control；失踪的control合法结算`NotSent`，不能删一个业务record或宣称remote receipt。任何真实非Fresh/越界ready仍fail-closed不放行。新增纯Rust7条过期parity与0-ready无拷贝回归。

H464 Normal C10独立真实Action41000374541 artifact12952983950：25ms/0%，60s Windows first10.0Mbps Linux9.9974Mbps，first fraction双方100%，真正双端owned Stop PASS。不同于Auto，该Family C10完整PASS但不外推C50/C300，亦不推物理性能/单向p99。

修复必须以新SOURCE真实Windows/Linux Auto原生首到、CPU、Stop复测，H466单测只是前置。A4/A5、B lifecycle、C高阶和300s继续待完成。

```feature-impact
{"kind":"updated","ids":["fec-auto","fec-fixed"],"reason":"Repair actual Linux original M1 parity/control expiry settlement, avoiding persistent BAD_STAGE and unauthorized stale PN retries; native Auto and Fixed high-loss revalidation required."}
```
