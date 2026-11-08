# PLAN028 H1353 — 真实 Game4 共同底层黑洞 / 正在收取结果

- 状态：**IN_PROGRESS / NOT_YET_VERIFIED**，不写业务 PASS；原始 H1352 随机损伤、H1317/H998 FAIL 保持各自结论。
- main 原子测试夹具提交：`104a5213c10e4869f948069071d8af4311403e91`；原始 Go TLS443 + Rust native M4/ISA-L 产品二进制 SOURCE `6c5fd909b9f42d1af89c698cdaabc79bbb72e589`。严格核 manifest/3 个 ELF SHA；不改产品、record、FEC、配置或热路径。
- 现行 H1259 原生五用户共享 TUN/五租约 + 两向 veth tc netem + 10ms app 桶复用；只在 `WBD_PLAN028_GAME4_CORRELATED_BLACKHOLE=1`、180s/pressure/stages2、真实静态 veth ARP 控制下启用测试线程，其他历史场景默认行为不变。
- 场景：Alice Normal Off、Bob Auto、Carol Game2 Off、Dave Game4 Fixed6、Erin Normal Fixed6；全体实际 authenticated 双向 UDP，Alice/Bob 同时 framed TCP。各方向 base=4/4/3/6/3 Mbps，phase scale 0.2/0.35/0.5/0.35，峰值合计 10 Mbps/方向；随机损伤0%，OS 单程 0/50/100/150/0ms，600s rotation 在180s内故意不触发，故**不算 L1 轮换**。
- 选择依据：上一 H1351 同类原生 x86 4vCPU 峰值合计19Mbps/方向宿主 busy42.34%（含发生器/内核/产品，非纯产品 CPU），本场降低至10Mbps/方向，避免负载饱和掩盖稳定故障。业务混合256/1024B，均值约794B，未计FEC/四lane的业务PPS近约1,575pps/方向；真实收包/外层PPS须读回，不能借此当压力证明。
- t=70..78s 在 Dave **同一共享物理 veth** 的两个 egress 方向同时置100% netem；其四个 Game lane 受共同 underlay 损伤，**不声称两条独立物理路径**。t=78恢复原始0%/150ms；比当前90s dead 参考短，不替代切网重认证专项。用两侧实际 `tc -s -j` drops（恢复前读，因为 qdisc replace 清计数）、单调时间戳、原始 app 10ms bins 和真实最终 Stop 来定因果。
- 明确独立判读：Game4 t=72..76s 应见持续发送但真正零收件，预期断流**不记健康 PASS**；t=82..102及110..145s 检恢复交付和750ms无收瓶颈，真实恢复后2.5s 首收作定向诊断门，非握手SLA。Alice/Bob/Carol/Erin 在 t=72..76s 需要真实持续双向业务而无跨用户秒级HOL；五个客户端 exact Stop、服务端共享 TUN 和每租约队列保持硬门。
- Actions：H1353 `42435004151` 预检 `128591854553` PASS、native `128591896534` 在途；旧 H1295 ARM64 `42435004153` 因其 workflow 的 `push.paths` 包含共享夹具被附带触发，单独收结论，不作主动重复测试。保持同一 H1353 Action，不刷 seed。若只是脚本/审计错误仅离线修。
- 后续：按 cursor 收产物并分级 PASS/FAIL/NOT_TRIGGERED/CAPACITY_LIMITED；保留原始失败。未覆盖 L1 七模式各两轮、Windows 真双设备、L2 常规大流量和相关黑洞恢复边界、L3 两场1800s，仍不关闭PLAN028。
