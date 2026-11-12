# M0｜PLAN028接续提示词

你在 `lly8666/wbd-next` 的main完成PLAN028；2026-11-07起**功能冻结、集成可靠性验收与缺陷收口**，不是无任务，也不提前宣布完成。先读START_HERE/AGENTS、[M0长期提示](M0.md)、registry/cursor、[028功能范围](../decisions/M0-PLAN028-SESSION-CONFIG-20261102.md)及[专项验收](../testing/PLAN028_INTEGRATION_ACCEPTANCE.md)。每轮默认上次中断，刷新main、核checkpoint后相关增量、先收在途Actions，补漏记事实后续做，别重复dispatch。历史优先事项只作参考，当前故障由最新证据决定。

1. **先整体定位，再最小修复。**恢复已有短测失败和未验证候选，核TLS认证→双方数据面就绪→MTU安装→交接→旧代Stop整条契约；不要只追最后报错处。条件修复没触发的PASS不能算修好。查现行调用链/相关历史再改，先选能区分假说的最小实验，不重复刷seed。
2. **你有现场决策权。**主动安排缺陷、实现、参数、观测和测试；结合PPS/BDP、实际FEC块/相关损伤、队列时延和宿主容量调整建议压力/样本长度/性能容差，先说明依据并保留原结果。保持标准建链、隔离、完整性、generation/原密文、MTU和owned Stop硬门。大胆细心做完整工作包，小脚本错误及时修，不造防御框架、不反复审批、不追噪声。
3. **复用当前成熟数据面。**不重写FEC/Auto/Game/机会式重复/record协议，不加稳态头、固定探针或Go热泵；只修真实接线缺口和已证热点。外层重复是廉价外观，不负责业务恢复。共用TUN按session/IP分发，旧代只释放自己，坏一client/lane不能堵兄弟。
4. **按专项计划递进。**L0确定性真实owner边界→L1七模式/多客户端/单端口/独立配置及路径生命周期→L2容量标定与弱网/恢复→L3冻结SOURCE后的代表性综合长测。充分覆盖TCP/UDP大小包、纯单向/双向/稀疏、轮换、idle/keepalive/Stop、MTU、单/双向黑洞；不是每个维度全排列。容量内秒级断流不能被平均吞吐/p99掩盖；VM满即停更重同族，产品单核/锁瓶颈不能甩给VM。
5. **沿现行契约接网。**用户默认外层完整IPv4 MTU1460B，1500仅显式最大值；内层自动预算/安装/读回，不覆盖用户意图/其他client。物理NIC、源IPv4或实际有效MTU变化，经200ms静默/最长500ms合并后走已有新代认证；单纯网关噪声、TUN事件不盲重连。200/500ms不是握手SLA。A可用时等B真实就绪再退休A，Game健康兄弟继续，休眠不自醒、Stop不复活。当前已验生命周期参数优先，老15s Health/90s dead/1–30s退避仅作成熟参考，不盲改回历史值。
6. **高效验真。**完整包两端/装配/配置/夹具齐后冻结SOURCE，按平台构建一次核manifest/hash复用；一Action一网测场景，不同Actions并行，同VM A/B顺序。Linux任务整平台x86双端/原生ARM64双端交替，Windows补真实Npcap/Wintun独有路径，不用QEMU或另一OS替代。有限日志/包头摘要，报表错误离线修，不为它重跑网络。
7. **完成完整目标再停止。**证据/devlog/功能卡/cursor沿现有体系，精确区分PASS/FAIL/NOT_RUN/NOT_TRIGGERED/CAPACITY_LIMITED。已有有效资格复用，原失败保留；028必需覆盖、已知阻断回归、容量边界和有限长测齐才交付。Android/物理未跑单列，不能藏技术阻断。已完后重复提示仅核新事实并说明完成，不自创新目标；后续029/030只有明确授权才继续。

本提示词只指路；具体方法、公式、覆盖和退出口径唯一维护在专项验收计划。运行SOURCE、待收结果及下一步仅在cursor/evidence，不把瞬时H号重新塞回长期提示。

**H1580接续导航（不把瞬时Action写成永久结论）：**按 [028覆盖与逐键配置表](../testing/PLAN028_M0_ACCEPTANCE_COVERAGE.md) 阅读已用正式入口、SOURCE、原始失败、源码修复和独立剩余验证。Windows V4正式CLI已默认native，GUI走同exe；SOURCE8a H1601签名Windows单Wintun＋四Linux150s真业务已验证自动租约、AES256/三AEAD共存，但不是Windows七模式全组合或独立DUT L3均通过。先收当前Actions、读实证据/receipt再派发，仍禁扩029/030。

**H1626交接校正：**旧审计中Win原生默认false/AutoLease:false/仅ChaCha的情形已被正式装配替换与SOURCE8a/H1601真实受保护/32和Rust cipher/OS应用证明；不重复重造协议。保持 MTU1460/FEC Off/Linux轮换0/Win15s-90s-idle0/outer repair on。当前缺独立 A管理+B非Runner Win DUT+C独立Linux 的真实1800s L3，禁止误用Windows hosted runner+WSL2；当前源其它未验项目看[覆盖表](../testing/PLAN028_M0_ACCEPTANCE_COVERAGE.md)。旧Action42979705842、42979705889失败保存，最新治理43113485314/43113485414成功。PLAN028继续IN_PROGRESS，029/030不动。
