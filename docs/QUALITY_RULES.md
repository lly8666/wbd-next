# 简洁与性能约束

- 解决当前任务，不预建插件系统、抽象工厂或分布式协调服务。
- 模块边界表达业务责任、所有权和资源寿命，不能只按“多几个 agent 好并行”拆代码。
- 热路径记录分配/复制/锁/系统调用/唤醒成本；没有测量不报 CPU 提升百分比。
- 行为硬门与调优参数分开，硬门不能靠修改预期通过。
- 每个新增队列/缓存给出容量、释放条件与满时行为。
- 有明确必要性才使用 unsafe、自制无锁或新依赖；成熟硬件加速库可以复用。
- 诊断默认关闭；不为 GUI 读数打开逐包大日志。
- 小修复不夹带大范围格式化或架构重排。
- 新参数落到配置/CLI/GUI/帮助/目录；不适用项记理由。
- 一项完成后按父级收益决定下一步，不无限追单个 seed 或局部微指标。

参考：[Google review](https://google.github.io/eng-practices/review/reviewer/looking-for.html)、[Rust API Guidelines](https://rust-lang.github.io/api-guidelines/checklist.html)。采用原则，不将指南全文转成机械硬门。
