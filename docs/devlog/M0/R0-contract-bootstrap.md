# R0-CONTRACT-001 子任务：共享类型和单目标构建消费闭环

- why_now：00/11要求M0首先冻结共享类型/来源/构建入口，防止M1–M4在未正式激活时各自定义BufferKey、MonoNs和ABI。
- 本次原子范围：固定Cargo workspace中的纯类型wbd-types、Rust 1.85.1；固定旧Go源码a7a82db31fe736ffedee330795a3234d358f1984（已从远端提交确认）及当时go.mod的go1.23.1 / toolchain go1.23.12；首个Linux x64 Actions build→上传预编译lib/test及SOURCE/size/hash清单→consume校验并直接执行测试。无外部crate/ISA-L/C依赖，也尚未新增C ABI。
- 类型版本边界：仅Rust内部值类型，非wire或repr(C)，BufferKey仅属其owner arena；generation到u32::MAX退休，MonoNs用checked/saturating，ConfigRevision不可回退；NoCapacity带资源种类。此处不定义额外wire格式，V4以00页为唯一规范。
- done_when（本子任务）：实质S完成以上文件，Actions build和consume实际结束且明确验证范围，独立cursor-only H引用精确SHA/run；若失败则记录partial而非凭workflow绿灯宣布PASS。
- 测试精确范围：wbd-types五项Rust单测（时钟溢出、修订重放、generation、身份类型、资源错误），+产物SOURCE/输入hash/size消费门；Actions系统中的治理检查独立。B01/A01/C01/I01等模块反例未覆盖。
- 未做：旧Go编译/原始V3向量、V4的24B admission golden、Go↔C ABI实际布局与旧size、platform ABI/真实驱动、Windows/ARM构建、ISA-L/AEAD、产品/物理/性能测试。不得将Python FEC代数PASS挪用。
- 本子任务结束后下一动作唯一：实际执行旧Go V3与V4 admission golden对照（Go已编译来源必须固定），作为后续ABI工作前置门；M1–M4保持reserved。
