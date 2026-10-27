# M0：Windows 接线整改与极限验收执行包

用户已授权你接续当前main，不重做已通过的接线。先结算当前在途Actions和未留痕结果，再读取当前main的registry/自己的cursor，以及 `docs/decisions/M0-WINDOWS-EXTREME-REMEDIATION-20261027.md` 和它指向的审计证据。其他设计按实际修改模块查，不全库读历史。

本次目标是真实首次交付、低延迟/无跨业务HOL、低系统成本；不是把所有Go代码翻译成Rust。用户要求：**先写完本整改包全部产品代码、调用方、测试用例、装配清单、有效参数读回和夹具，再冻结同一个SOURCE统一跑Actions**。包内连续开发，不每修一个helper启动全链路，也不为已有Normal正例反复刷绿。静态检查可随写随做，执行验证仍在Actions。当前正在跑的任务正常结算，不重复dispatch。

按方案A→B→C→D→E完成：自然Auto的真实TX序号故障、FEC take后分配失败丢状态、长期缺口下半回绕误拒；删除1536 repair credit对fresh的闸门；设备租约代替逐包OS身份查询、缓存DLL接口、有界批量FFI/复用缓冲、合理事件唤醒；统一repair绝对帽/池/Auto成熟窗口与有界清理；Game单lane故障隔离、真实完成和动态MTU/LINK兼容；修复失效测试装配并补足CPU/队列/业务观测。静态确定与待复现根因分开，禁止关闭硬门、伪造Applied/ACK、降低自然Auto阈值。

完成后一次构建Win/Linux/ARM64配套包并复用：先编译/core/receipt和平台回归，一次真实多模式功能批次，再按方案矩阵跑独立性能Action。每Action一个场景/一个测量job，新旧A/B在同VM顺序；独立环境可并行。容量不足停止更重同族，区分环境不足与产品单核瓶颈，不刷seed。重点500M线路/200ms/2%、单TCP应用500M/200ms/0损、50M线路/300ms/30%最高FEC、Game独立/共同损伤、混跑无HOL、MTU边界。源码问题修完仅回归原反例和受影响保护，不全矩阵重来。

原始Auto失败/四个receipt失败必须原样保留。1Hz进程CPU含Go+Rust DLL，不能按EXE名推断语言开销；补一条短栈采样诊断，正式性能关掉高成本profiling。未完成的单公共端口/认证等旧功能恢复另批，不借本次整改无限扩包。

使用现有devlog/cursor/evidence和feature卡记录effective参数、SOURCE、run/artifact、结果和剩余项。不要覆盖其他工位状态，不增新治理流程。满足本批范围后交付结果表，物理机/全局GUI/WFP/历史80s等未测范围明确保留。
