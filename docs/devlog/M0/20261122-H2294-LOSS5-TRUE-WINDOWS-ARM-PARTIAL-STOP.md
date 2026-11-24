# PLAN029/P1 H2294 · 5% 原生机会式密文修复：单组完整、第二组中继失联（2026-11-22）

真实 SOURCE `7d651fcd5c897d5c2178db10b93e13b6ed14f9d5`，[Action 45032406637](https://github.com/lly8666/wbd-next/actions/runs/45032406637) **FAIL，不能冒充9/9**。双组独立 Win2025 签名 Npcap/Wintun 原 GoTLS/Rust→原生 ARM kernel 双向200ms/5% netem relay→原生 ARM GoTLS/Rust TUN；FEC全程OFF，只切一次原冻结密文机会修复 `A OFF → B ON → A′ OFF`。Windows a/relay a/ARM a 三腿真实成功，Windows b A和B真实业务/Stop成功，但 b 的第三腿在 `H2276_RELAY_UDP_CONTROL_NOT_REACHABLE` 丢失中继控制且 ARM b 失败，故**双组完整因果资格失败**，不强派同配置试验掩盖原因。

| group | A关 Mbps | B开 Mbps | A′关 Mbps | B真正NPF核接受冻结原密文份数 |
|---|---:|---:|---:|---:|
|a|0.525|0.760|0.837|**12**|
|b|0.422|0.713|**NOT_RUN（中继失联）**|**13**|

a组 B 相对同机 A/A′ goodput 均值 **+11.601%**，但 P99 A/B/A′ 1734/1125/1375ms，late>1s 28/6/22，baseline 自身明显上漂，且B实际包量和物理容量未证明稳定。b组虽B比A +68.957%，但 A′ 不存在，**禁止用这个提升充作双组三腿PASS**。真实对端ARM收到客户端bulk字节：a A/B/A′ `10911744 / 11108352 / 11403264`；b A/B `10862592 / 10993664`。真实两向内核丢包分别在附JSON中，全阶段 A和B `sparse_echo_received=160`、Win原GoTLS/Rust Stop PASS。

**重传事实**：历史 P1 wrapper 在原 Windows诊断 JSON里输出 `actual_original_native_frozen_repair_packets=0`，是**错误的关闭前定期快照**；真实 Windows2025原Rust Stop（原始工件 [a14758149166](https://github.com/lly8666/wbd-next/actions/runs/45032406637/artifacts/14758149166) / [b14758960601](https://github.com/lly8666/wbd-next/actions/runs/45032406637/artifacts/14758960601)）有三个独立相关行：
- a B `M2_OPPORTUNITY_STOP candidate_first=249 repair_accepted=12 repair_abandoned=237 repair_polls=17298`，`OUTER_REPAIR repair_packets=12 repair_accepted_wire_bytes=2857 r_to_f_ppm=218`，`OUTER_CURSOR unique_candidates=253 checked_once=491`。
- b B `candidate_first=248 repair_accepted=13 repair_abandoned=235 repair_polls=19476`、`OUTER_REPAIR repair_packets=13 repair_accepted_wire_bytes=1959 r_to_f_ppm=151`、`OUTER_CURSOR unique_candidates=256 checked_once=494`。两个 B 的 `authenticated_reverse_reports=0`。A/A′ 原生零accepted。

该 SOURCE 从定期快照旧字段推测0属于夹具统计缺陷，已由后继 `H2316 c9f9141331553dde494cb2e1f7c76ed464467781` 改为以真实 joined Stop+outer-repair两份独立accepted计数守恒，**不会篡改本Action当时产生的receipt**。修复是确实发生的但仅数十次，占总源字节 R/F 极少，不能证明对5%丢包的内层TCP cwnd有稳定补救。下一步先定位 b组为什么 third-leg relay control 消失（WSL boot ID / kernel netem / Tailscale direct vs DERP、runner生命周期/CPU），否则不重复同一批真实3R。
