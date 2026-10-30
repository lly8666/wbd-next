# PLAN027 H444｜Linux Fixed 的一次性认证质量启动确认（源码候选）

H442真实FEC source/parity→TUN交付但 Fixed Applied 永久等待退役WBC4。H444复用已有Rust M3-unique的加密START/CLOSE/Quality v2 summary，针对待确认Fixed创建 bounded TX/RX sampler，`bootstrap_only` 硬限制 **最多两个1024-PN窗口**，不会把Fixed变为无限Auto采样；Normal/off无变化。Rust `wbd_m0_embedded_go_fixed_commit_mature_m2` 只在真实 source+parity已被M4驱动复制、匹配rev、无staged PN、当前revision的认证质量确有正向覆盖和摘要后，才能回报Applied；否则维持Pending。旧M2位图不再参与新固定档分支。Native FEC quality readback也指向新样本而非非Auto旧M2。**尚未通过新SOURCE编译、真实双端和120s/5min**，本源码绝不标PASS；Windows对应Fixed认证与A/B/C继续。

```feature-impact
{"kind":"none","ids":[],"reason":"Candidate source wiring only; exact-source real Fixed validation pending."}
```
