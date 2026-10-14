# R0 原生 Go↔C↔Rust ABI 探针收据

2026-10-14。开工前重新读取main 的五个治理入口、M0 fixed prompt、00/11，验证 M0 active main/epoch1/revision1，cursor seq8 checkpoint `be61dba3abfeea8d9f2df24d9a85d88640e1c6e4` 到远端HEAD `4fec779ccbafb5f0f548bfe0e1b265130b11caaf` 只有一个cursor-only H；Actions 全部完成且无 open PR，判定 CLEAN。

**why_now**：前一任务为真实Go控制 V4 admission 建立严格早期拒绝，后续要对Go与Rust之间的实际C ABI做原生编译/调用。这个测试不能用Python模型假定内存布局和generation正确。

**S源码**：`b719f28ac2b112150e39133a9cabc8e7d32b8771`，Cargo workspace新增 `crates/wbd-engine` 唯一导出 `cdylib`（R0 probe sentinel），`wbd-types` 只读纯Rust类型；C权威头 `r0/abi/include/wbd_abi.h` 定义 ABI version1、info 24B、config16B、两个opaque token各8B、固定错误码。C ABI带显式config input_size，先拒旧大小再读取配置；token含namespace + slot + 32bit generation、不藏指针、generation耗尽永不复用、engine关闭使其所有lane失效；限制4 engine/16 lane仅作为探针压力门，不能当产品值。能力位始终0，不广告receipt/Game。

**真实执行**：固定Go仓库 `lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984` 的临时 Actions checkout 新增 `internal/r0bridge` cgo测试，直接链接在同一job由Rust1.85.1编出的 `libwbd_engine.so`；原生gcc C11编译`r0_abi_c`，Rust单元测试编为单独二进制。Go1.23.12 native linux/amd64。`build`仅编译四份产物，`consume`下载后验证双source/run/架构、13份输入文件和所有二进制size/SHA256后复用执行三种语言，未重新编译。

[Actions native ABI run 38514286818](https://github.com/lly8666/wbd-next/actions/runs/38514286818) attempt1 success，build job115689490267 / consume job115689666206：Rust 3/3 PASS、native C smoke PASS、Go cgo 4/4 PASS；旧size/version、未知flags、null、错误码、generation过期/交叉token/父关闭和容量反例通过。build ZIP id11869919968 sha256 `a0de3ee97a6227ccfcdf92df2d11165ff069c2e474ec0ddb97f9d451216c5a56`，result ZIP id11871535056 sha256 `842dbf65aa102bb0be789bddb7c7e4f881fb8bf8d6e329e1c8b29b524f3f51f5`；四份二进制摘要与测试日志摘要见 `docs/evidence/M0/R0-native-abi.json`。archive只来自GitHub的sha，未独立下载zip。相同SOURCE的 [Rust build run 38514286840](https://github.com/lly8666/wbd-next/actions/runs/38514286840) 与 [Governance run 38514286805](https://github.com/lly8666/wbd-next/actions/runs/38514286805) 均成功但各只代表其job范围。

**重要界限**：探针Go桥是固定旧Go source临时树的测试包，不等于老应用直接链接Rust；并未实施完整wbd-engine、V4数据能力、epoch release/业务收发或生产部署。真实C ABI布局只在linux x64验证，Windows/ARM/驱动/fakeclock/多target/产品/性能/物理仍NOT_RUN。接入Rust业务前必须有对应能力与生命周期资格，不得因为ABI probe绿色而解除Go生产V4的fail-closed门。

**本原子done_when**：源码、C/Go/Rust原生二进制通过精确Actions验证并记录source/artifact/未测，已满足。R0整体仍partial，M1–M4继续reserved。

**唯一next_action**：按00/11单独施工 R0 fake-clock 与 fake-platform driver 的 accepted_prefix/uncertain_index、borrow/close 边界和失败PN不可复用原生反例；Actions一次编译/复用，之后再开展Windows/ARM平台ABI构建检查。
