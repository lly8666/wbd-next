# PLAN027 H917｜一次 SOURCE 冻结并行四场景，不重跑已达容量的 Game4

- 收取已结束原生 [H915 Normal100 同 VM OFF→ON run41420996043](https://github.com/lly8666/wbd-next/actions/runs/41420996043)：真实同一 Windows runner、同源 H908 EXE+DLL / Linux Rust+Go，0% 25ms 60s；OFF CPU16.4062s，ON CPU19.2188s，**ΔCPU+2.8126s**（ON分母14.635%），ON R281B/F825927818B≈0.000034%，仅两包补发，两个leg全双端 Stop PASS、首到均≥99.9993%。Go冷TLS、OS、Stop含在 CPU，不把差值伪称算法独占，跨VM H912 ON100 CPU不作对照。与 H884 同VM 30% ΔCPU -0.3594s并列，真实正成本更接近压力/缓存/OS管理路径，暂不因小量错误追求PTO微调。
- 收取 [H916 Game4FEC6 OFF20M250ms30 run41422017446](https://github.com/lly8666/wbd-next/actions/runs/41422017446)：真实原Windows+WSL2 双向业务20Mbps/dir，初达Win .999627 Linux .998594，4lane最高档、外层R OFF、双Stop PASS。Windows本产品进程 CPU36.125s/76.265s≈47.368%一核、峰值RSS61,136,896B；F/C 全Game聚合字节、跨OS单向p99未计量。10M旧 ~9.35x lane COPY数量**非字节**。在20M同族高损已过，不能从此推测更重场景必要，也不再堆 Game4 20M ON/更高带宽。
- H917 **四条独立 workflow_dispatch Actions** 并行，独立 Windows2025 VM/WSL2，单Action单场景，SOURCE fixture H917本提交，**产品二进制仍固定 H908 `6693910f...` run41415722303 严格 manifest/hash 下载复用**；preflight 校验 HEAD 恰好H917 才允许 dispatch，失配即停止。①既有 V2 Normal OFF10M25ms0% 两次实际内核100/300ms loss bursts（~0.67%时间黑洞，独立于随机drop），64/128/512/1200B混合平均753.6B≈1659 source PPS/dir；②Auto ON10M250ms不对称1→15→30→1% / 5→0，240s，最后150s低损观察≥120s，910.8B≈1372PPS/dir；③Normal ON10M25ms1% 300s，平均753.6B≈1659 PPS/dir，双向持续UDP、小包混合、真实TCP smoke，**不得称持续TCP+UDP混合长测**；④Fixed6 OFF 50M25ms0 60s，1115.56B≈5603PPS/dir，最高FEC实际额外字节不得以理想k:r代替测量。
- RTT业务 BDP：①③25ms×2=50ms，10M≈62.5kB/dir；②250ms×2=500ms，10M≈625kB/dir；④50M×50ms≈312.5kB/dir，未含FEC、多lane/驱动buffer；PPS是业务payload下界。各Action需读回真实tc/drop、端点吞吐首到/p99/超时/Stop、F/R/C（能拿则取、拿不到NOT_MEASURED），不把Green workflow当性能或跨SOURCE证明。阶段在提交时 **NOT_RUN**。
- H890历史 Normal ON10M0% 300s已验，批次③是新低损小包/ON成本时长证据而非重跑旧工况。H908 105s真实双OS恢复已通过；无物理机部署、无产品/GUI更改。

```feature-impact
{"kind":"none","ids":[],"reason":"Archive source-specific native PASS receipts and dispatch four independent unqualified PLAN027 network/Auto/long-run capacity gaps using unchanged signed H908 product binaries and existing workflow controls."}
```
