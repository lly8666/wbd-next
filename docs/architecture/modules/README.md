# 模块施工说明 v2

这套说明用于直接实施，补齐上一版总方案留给实现者的选择；已实现/已测范围只读当前 cursor/evidence，不从施工说明推断产品已完成或尚未开工。优先级：用户要求/章程 → 本目录明确修订 → 总方案 → 原项目历史；不允许按旧聊天另选一套架构。

| 编号 / 文件 | 唯一职责 | 执行角色 |
|---|---|---|
| [00-CONTRACTS](00-CONTRACTS.md) | crate依赖、类型、错误、跨模块顺序、版本 | M0 |
| [01-CONTROL-BRIDGE](01-CONTROL-BRIDGE.md) | Go/Rust ABI、bootstrap切换、关闭 | M4，公共ABI归M0 |
| [02-RUNTIME](02-RUNTIME.md) | TX/RX owner、唤醒、公平调度、时钟 | M1 |
| [03-MEMORY](03-MEMORY.md) | 池、冻结、引用、回收、总预算 | M1 |
| [04-CARRIER-IO](04-CARRIER-IO.md) | TCP外观、批量I/O、平台返回值 | M4 |
| [05-RECORD-CRYPTO](05-RECORD-CRYPTO.md) | AEAD/HP/PN、record解析、去重 | M3 |
| [06-LINK-MTU](06-LINK-MTU.md) | 分片、重组、路径预算 | M3 |
| [07-FEC](07-FEC.md) | 编码、缺源恢复、block生命周期 | M3 |
| [08-RECOVERY](08-RECOVERY.md) | 真实receipt、shadow、RACK/PTO、预算 | M2 |
| [09-PIPELINE-GAME](09-PIPELINE-GAME.md) | Normal/Game组合、共享恢复、慢lane | M1 |
| [10-LIFECYCLE-QUALITY](10-LIFECYCLE-QUALITY.md) | 原策略接入、状态快照、配置生效 | M4 |
| [11-IMPLEMENTATION-GATES](11-IMPLEMENTATION-GATES.md) | 开工顺序、反例、构建与交付边界 | M0协调 |

新agent只读本模块、00公共契约及直接依赖，不要求一次吞下全部文档。当前任务分配读 main registry，执行进度和来源读登记分支 cursor，不在这里建第二套进度系统。

## 本轮作出的具体修订

1. 不为每条lane/每个block建线程；两方向分owner，平台阻塞reader有界例外。SPSC采用rtrb，唤醒协议必须二次检查，不能仅看empty边沿。
2. `frozen wire`指TLS-like record及其TCP seq绑定；TCP ACK/IP头等发送外观可重新生成。当前旧版稳态data并没有TCP timestamp option，不能凭想象添加。
3. 真实确认采用明确位图，未报告不等于丢失；删除“真实累计前缀必须一直前进”的依赖，避免control PN/失败预留PN形成永久洞。反馈只随待反馈数据活动产生。
4. ISA-L仍用旧GF256矩阵，但解码只对e个缺源做e×e求逆，再构造直接输出矩阵。避免每次固定20×20求逆和重建parity。
5. 去重窗口按恢复寿命/PPS计算；超过窗口明确late，不退化成无界map或忘记历史后重复业务交付。
6. 队列/计时器内存一起计入shadow：64B hot entry + 24B timer node + 索引/对齐余量，模型改用96B/slot预算；不是已测Rust布局。
7. admission明确升级为V4并绑定新能力/逻辑epoch；复用原一次受TLS保护的请求/回复，不增加往返。不谎称Game新格式能无协商与旧端兼容。
8. 反馈顺序包可合并10ms，所以PTO按10ms而非gap的2ms计余量；RACK按经过时间判定，避免高包率下相邻发送时间很近导致永远不修复。

每页包含：选型理由、状态/接口、执行顺序、资源界限、必测反例和禁止事项。若实现遇到矛盾，先用最小反例给M0修改契约，不通过隐蔽fallback绕过硬门。
