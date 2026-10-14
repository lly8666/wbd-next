# R0：Windows x64 / Linux ARM64 跨目标 ABI 构建门（M0）

2026-10-14。远端main HEAD `946e364deb5d9027198904f1f139afee9463529b`；M0 cursor seq10、checkpoint `40a2a343d1f937f2aff4d9136147cef6ddef8263` 到HEAD仅一笔cursor-only H；全部旧Actions完成success、0 open PR，M0 active/main/epoch1/reservation1，CLEAN。

**为什么现在做**：上轮Linux x64 Go↔C↔Rust native ABI / Rust fake driver绿灯不能证明Windows或ARM目标ABI可编译。先验证真实交叉目标二进制、定宽C struct ABI和导出符号，再判R0剩余门；不造假的native运行资格。

**本轮原子范围**：独立workflow`.github/workflows/r0-cross-abi.yml`运行于 Ubuntu 24.04 x86_64，使用 Rust 1.85.1 并rustup安装`aarch64-unknown-linux-gnu`与`x86_64-pc-windows-gnu`目标标准库；GCC cross compiler（aarch64-linux-gnu-gcc / x86_64-w64-mingw32-gcc）生成目标C可执行文件。编译既有`wbd-engine` R0 sentinel cdylib与`wbd-platform` rlib（不把wbd-engine视为可用数据面）。由目标C编译器对 `r0/abi/include/wbd_abi.h` 进行 sizeof/alignof/offsetof 静态断言，并链接真实目标Rust动态库的五个R0导出函数；仅生成，不运行目标程序。

**编译-消费**：每目标独立build job，在manifest记录精确新SOURCE/run/attempt/Rust/target/目标C编译器/输入文件SHA256与三份二进制SHA256+bytes。独立consume job下载相同target+run+attempt artifact，严格核对已编译文件hash和全部输入文件hash，读取 ELF64 AArch64 (e_machine=183) 或 PE32+ x86_64 (machine=0x8664) 的真实文件头，利用目标binutils读取`.so`/`.dll`的五个动态符号，产出仅`CROSS_BUILD_PASS`或FAIL。**绝不运行DLL/SO、Windows EXE或ARM ELF**；host即使可运行仿真器也不将其当目标原生执行。

**本轮 done_when**：两个targets各自交叉编译、目标C静态ABI断言与链接成功、consumer校验成功；记录精确SHA/run/jobs/artifacts与Linux native回归的独立来源/界限；推证据S与cursor-only H。若单目标失败，只依据具体真实日志修复，不虚构两个目标全绿。

**范围之外**：目标OS native execution、真实kernel syscall/driver、ARM/Windows上的Go↔C动态调用、GUI/安装、Rust稳态引擎和V4 features，产品/性能/物理全部NOT_RUN。仍为R0 foundational partial，不激活M1–M4，不开放Go控制的V4生产门。

**通过后唯一下一动作**：审查R0退出合同与test ID/source-lock实际覆盖状态，列出尚未实现的公共codec（receipt bundle/Game envelope）与旧Go V4对照的精确反例，并先做最小生产无害codec golden/边界与Actions消费者；只有形成足够共享foundation才考虑正式角色分配。
