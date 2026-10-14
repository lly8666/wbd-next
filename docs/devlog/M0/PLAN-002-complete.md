# PLAN-002完成：12份模块施工说明，模型与治理通过

2026-10-14。精确设计/工具SOURCE `ac1ac76dbac92b7ffb494efca65064751a28b91b`，Actions [38505985662](https://github.com/lly8666/wbd-next/actions/runs/38505985662)，attempt1，job115663490787，SUCCESS。51项自动检查通过，下载artifact11866963650，archive SHA-256和manifest内7份文件size/hash逐项核过，0 mismatch。结构化证据在`docs/evidence/M0/PLAN-002-module-design.json`。

FEC代数模型：1065组覆盖active k1..20、全部6个配置档和每个可修缺源数量；小k1..4另98组枚举所有缺源/所选parity组合，共1163组。e×e解法、完整20×20选行求逆与原始数据一致。这里**没有**运行编译后的旧Go、Rust或ISA-L；这些仍是R0/R3必做门。数学核对不能当产品性能资格。

成本模型已包含96B/slot元数据、10ms顺序反馈上界。RTT150/300ms、RTTVAR5ms的PTO为180/330ms，cache为410/710ms。内层500Mbps/方向、1200B、RTT300ms示例shadow约73.711MiB；128B约153.798MiB，超过默认128MiB，应选择容量档或诚实降低修复覆盖。没有宣称500Mbps实测通过。

12页施工说明涵盖公共协议/ABI、Go桥接、运行时、内存、raw/TUN/Npcap I/O、AEAD、MTU/LINK、FEC、恢复、Game、控制功能接入和实施门。每页明确输入/输出或状态、所有权/预算、错误退化、必测反例与禁止事项。M0–M4固定提示词已经指向各自页，START_HERE保留有限读取，日常进度仍只在cursor/devlog。

特别保留：旧项目未关闭的N2/N4、MTU压力与80s下行问题；真实业务首到和无HOL、cipher/generation/身份/MTU硬门；原Go建连/管理方案；Actions编译复用、同job顺序AB/BA、容量停止规则。V4首次Game先取得共同epoch再并行其他lane，因为旧TunnelID可能稳定复用，不能把它误当本次运行代次。

未启动Rust产品实现、未改旧源/部署、M1–M4仍reserved。下一项R0-CONTRACT-001：按00/11冻结实际Go向量/ABI/依赖/build manifest，再分配并行工作。当前任务到此收口，随后H仅确认cursor。push的已知admin bypass未隐藏、未修改保护设置；真正测试结论来自上面精确run。
