# WBD Next｜项目长期目标与不可退让边界

**目标**：保留原成熟TLS/系统冷控制，以Rust长寿命native数据面降低**全产品**CPU/内存/唤醒并改善真实业务首次交付。优先级：真实first-delivery、低延迟无跨业务HOL、系统成本、最后才是附加复杂度。可用有界内存换CPU；语言名称本身不等于CPU归因。

**不可退让**：真实认证/完整性、用户及lane隔离、epoch/generation、MTU/PMTU、合法报文/PN/重放窗口、真实驱动结果、原密文修复（同Seq不可重封）、有界队列/次数/寿命/资源和owned Stop/WAL恢复。独立新业务包不等旧ACK/FEC block/坏lane，缺失或不确定反馈绝不算零损/确认；不为控制包造ACK循环。允许TLS-like/TCP-like设计目标，不宣称流量不可识别。默认不自造新TLS、TCP栈、加密格式、FEC矩阵。

**外层机会式修复**：仅低CPU、最多一次、无持续DATA PTO；高负载总修复约≤10% DATA字节，稀疏业务不受相同比例限制但仍受绝对资源边界。来源见`docs/decisions/NETWORK-OPPORTUNISTIC-REPAIR-MTU-20261023.md`，历史数值如50M/30%、500M/2%、单内层TCP500M/200ms是性能目标，资格与容量以实测区分，不替代安全/Stop硬门。原FEC RS20档只做迁移行为oracle，新协议使用`docs/architecture/FEC_V2_BALANCED.md`真实FEC2 k≤16。

**平台职责**：Windows原Go FakeTCP/TLS、WFP/DNS/route/WAL/GUI和低频建链；Rust唯一Windows Wintun/Npcap稳态owner；Linux保留已有原Rust raw/TUN成熟路径。Game2/4无Auto，Normal可Fixed/Auto；Keepalive、真实业务idle、无认证dead、FIN/DORMANT必须区分。最新细化授权见main `registry.goal`与其当前决策，不从本章程推断项目进度。

**交付证据**：代码/组件PASS≠真实双端/性能/物理PASS。同一SOURCE构建固定manifest、Actions真业务/Stop验证、同runner顺序A/B对CPU；按容量停止更重同族，保留旧FAIL/未测风险。更新功能目录与可见参数，不默认动用户物理机器、无凭据/正文进入仓库。旧目标与分支背景详见`docs/history/2026-10-28-M0-MAIN-HANDOFF.md`及归档决策。

**治理**：G1授权包自主做；G2模块/责任边界变更记录影响；G3更改硬要求/未授权外部部署需先取得决定。源码/成果在main；角色/真实进展见main registry/cursor。