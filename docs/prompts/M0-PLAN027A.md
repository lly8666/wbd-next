# M0｜PLAN027A MTU统一开工/接续

你继续lly8666/wbd-next主线。先按START_HERE/AGENTS/M0长期提示词恢复最新main、registry/cursor与在途Actions，默认上轮被打断；只追相关增量，先收已有结果不重复dispatch。

任务顺序已由用户指定：027收口→027A→028。本包入口 `docs/decisions/M0-PLAN027A-MTU-UNIFICATION-20261102.md`，唯一规范 `docs/architecture/MTU_CONTRACT.md`。若027仍在运行，别抢写其同一模块；其MTU阻断可摘最小根因修复并留痕，其他内容完成后登记027A继续。用户直接调用本提示词即为本包施工指令，无需再次逐项请示。

目标：所有端/模式统一外层IP、MSS/options、record与内层MTU；修GameFEC遗漏type1的1399→1398；去掉重复公式/隐藏帽和inner当outer传值。Rust纯预算为权威，Go冷ABI复用，OS applied有真实回执。不是把所有MTU改成一个相同整数，不为统一重写网络栈。

大包按IP语义：普通TCP让OS分段，合法IPv4 DF0优先内核分片、必要时共享有界慢路径；DF1超限给正确ICMP/EMSGSIZE。保留已接通Normal LINK兼容，不虚称Windows/FEC/Game均有LINK。不把单个oversize升级为Stop，不用改密文/跨lane重用救旧repair，不强求30%loss下大UDP零丢。Auto/lane/方向预算与固定密文规则见规范。

先读当前实际调用链及旧成熟实现再修；新source和规范矛盾要依据实际编码/标准修订并留理由，别机械照附件。连续写齐同批双方代码、ABI/配置/帮助、夹具与功能卡后一次构建复用SOURCE/manifest/hash。一个Action一个测量场景，不同场景独立并行；新旧同VM顺序比较；先界值再原生小矩阵/两条弱网与保护性能，不重刷027全速率表。

真实业务首到、低延迟/无跨流HOL、低CPU优先。大胆自主做普通决策，计算PPS/分片残损与实际成本，容量不足停更重同族；异常定位最窄环节，不堆防御框架、不刷seed或小数点。复用027生命周期，不能另写恢复器。

每批短devlog/功能卡/evidence，阶段更新cursor，精确SOURCE与FAIL/NOT_RUN保留；中断缺记录先补事实。整包退出条件齐后交付并接已授权028；若后续尚未启动则给入口待验收，重复提示不要无目标扩测。
