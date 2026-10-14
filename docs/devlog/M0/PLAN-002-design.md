# PLAN-002：逐模块施工设计与代数校核

2026-10-14，用户要求模块架构细化到后续实现agent无需重做核心选择。先核远端main `86a28a922462680a2d859531be5cb3f99425e493`、M0 epoch1/registry1及既有交接，未重复旧Actions/未改旧仓库源码/未操作物理机器。原方案PLAN-001保留，新增`architecture/modules/`索引及00–11共12份说明，不建立第二套进度体系。

读固定旧SOURCE a7a82db的bootstrap/transition、record/KDF/HP、admission、FEC/fragment、Npcap发送返回语义，并核官方ISA-L、aws-lc-rs、rtrb/Mio/Tokio、Quinn、Wintun/Npcap及RACK规范。选择/来源见SOURCES_AND_DECISIONS；原始聊天/凭据不发布。

本轮明确：Go冷桥接和未确认握手尾部、V4一次受保护协商、owner/SPSC防漏唤醒、分页池与有限归还、96B/slot内存、原密文/动态外观头、真实receipt位图、重发预算/epoch、FEC缺源e维解法、Game共享编解码和慢lane隔离、配置/idle/自动档复用。PTO的反馈等待从2ms纠正为10ms，与顺序报告期限相符；RACK不要求相邻发送时间相差W。

新增Python代数参照检查e维解法、完整20维选行解法、原始数据三方一致；覆盖全部active k与配置档/缺源数量、小k全部可选缺源/parity集合。仅在Actions运行。该模型不替代旧Go编译向量、ISA-L wrapper内存安全、真实CPU或完整产品验收。

治理/成本模型和模块反例测试在本次push自动Governance执行，不另dispatch重复run。当前写此日志时结果未出，保持unverified=true、产品NOT_STARTED/NOT_RUN。验明精确artifact后再写完成记录/H；M1–M4仍reserved，下一开发阶段R0再激活。
