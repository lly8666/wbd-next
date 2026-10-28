# WBD Next：所有 agent 的共同入口

1. 用户最新指令优先。真实业务首次到达第一，低延迟、无跨业务 HOL、低 CPU；允许有界内存换 CPU。必要完整性、账号/地址隔离、generation、固定密文重传、MTU、owned Stop 不变。目的见 PROJECT_CHARTER.md。
2. **2026-10-28：M0 后续直接在 main 开发、测试和留痕。** main 是 M0 源码与当前任务的唯一入口，不再把产品代码放实验分支、只把进度抄回 main。这覆盖旧“所有新功能必须先开 experiment”对 M0 的要求。仅明确另授的并行独立任务继续指定分支。
3. **Windows方案B新授权：Go仅FakeTCP/TLS及OS/GUI冷控制，Rust独占Wintun/Npcap稳态业务、M2/FEC/Game/Health；换lane Go低频建链、Rust原子切换。** M0按 main registry.goal 的当前授权施工包连续写齐产品、测试、装配，再集中Actions/同机A/B；Normal/off成本验证后再移其余模式。保持Linux现有原Rust路径和认证/PN/WAL/Stop必要硬门；不写多余防御包装。
4. 新聊天/恢复先读 START_HERE.md，刷新 origin/main；任务取 main registry，事实取 main 的 M0 cursor，资格取精确 SOURCE 的 evidence/Actions。只核 checkpoint 后增量和已登记在途 run，不全仓扫描历史/分支。
5. **独立 FEC 工位历史任务已完成、归档。** 不执行旧 FEC status 的 next_action，不恢复旧“不合 main/Windows 暂跳”等岗位约束。历史实现/失败仍有用，入口 docs/testing/FEC_AUTONOMOUS_WORK.md；现存产品问题由 M0 当前包处理。M1–M4 已有权限不因本条自动新增或撤销。
6. 单一 main 写入者。接手已有 main 本地变更先辨认归属，不 reset/force push/覆盖；有真实并行写冲突才协调。已有开发/夹具分支仅做一次差异核对，必要增量合回 main，不整树覆盖、不按日期挑新代码。
7. 完整批次先写齐产品、调用方、配置读回、测试用例、装配清单与夹具，再冻结 SOURCE 集中 Actions 验证；静态检查随写随做。编译失败先便宜修复。不要每个 helper 启动全链路，也不把数个独立批次无限并成大重写。
8. 所有执行验证在 Actions。功能可合批；性能每 Action 一个场景、一个测量 job；旧新在同 job/VM 顺序 A/B。独立场景可并行，构建一次按 SHA/manifest 复用；达到容量瓶颈停止更重同族，不刷 seed。
9. 失败先取首个错误，回读相关设计、调用链及最近修复，再修并回归原反例和受影响保护。历史 PASS 不转移到新 SOURCE/平台，FAIL/NOT_RUN/容量限制不删；文档/治理检查不冒充产品资格。
10. 功能已接线的精确 SOURCE 正向 Actions 可开放网络试验，无须预先等物理/全部矩阵；不因此放开未实现功能或掩盖认证/OS/Stop 失败。
11. 功能唯一入口 docs/features/README.md。新增、改默认、平台接线/删除同步功能卡、适用 CLI/config/GUI/帮助和 devlog feature-impact。main 上未资格功能仍为 experimental，不自动正式化。
12. 一批次一份简短 intent（可随代码提交），开发连续推进；交付/暂停/恢复边界再更新自己的 cursor。中断未记事实要恢复并注明 recovered，不编造。达到 done_when 就交付，不等用户反复“继续”。
13. 热入口只留当前逻辑、未解决项及查找路径。阶段完成或热摘要变长时压缩；细节留原 devlog/evidence/Git，引用旧任务不能复活旧授权。治理详则按需读 docs/GOVERNANCE.md。
14. 凭据、私钥、业务正文、大 pcap 不进公开仓库；观测有界，清理自己产生的大文件，保留摘要/hash/失败。未授权物理部署不执行。

当前整改包由 main registry.goal 指向；本文件不保存滚动 SOURCE、Action 编号或逐轮待办。
