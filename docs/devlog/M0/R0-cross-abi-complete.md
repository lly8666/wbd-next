# R0 Linux ARM64 + Windows x64 跨目标 ABI/Layout 实际构建收据

2026-10-14，M0。启动前刷新远端main/roles/cursor seq10/00和11，checkpoint `40a2a343d1f937f2aff4d9136147cef6ddef8263` 至 HEAD `946e364deb5d9027198904f1f139afee9463529b` 仅一个cursor-only H，旧Actions全绿，0 open PR，M0 active main epoch1/rev1，CLEAN。

**why_now/done_when**：上一轮 Linux x64 native Go-C-Rust ABI、R0 Fake TxDriver PASS，仍无 Windows x64/Linux ARM64 编译资格。本轮只锁定跨目标Rust engine ABI sentinel和platform rlib，目标C布局静态断言+真实链接，独立消费对机器类型/导出函数/hash复核，不执行其他架构程序；目标程序只可能由后续真实相应runner测试。

**实质提交**：
- [`148202e0`](https://github.com/lly8666/wbd-next/commit/148202e0ec17ed693687c0c97582809e7b329eda)：`r0/abi/tests/cross_layout.c`、`tools/r0_cross_abi.py` 与 `r0-cross-abi.yml`。首run [38517436489](https://github.com/lly8666/wbd-next/actions/runs/38517436489) **failure**：Windows job115699286940 成功编译，ARM job115699286631链接Rust时`aarch64-linux-gnu-gcc`报`cannot find crti.o`，缺 ARM target libc开发包；因needs matrix失败而跳过consume，不将Windows单项成功当整体合格。这条事实保留。
- [`8ce2224`](https://github.com/lly8666/wbd-next/commit/8ce2224a734d45490c66b582f53057f1bfd40ae2)：仅在 ARM64 cross包依赖增加`libc6-dev-arm64-cross`，不改变ABI源码/断言标准。回归run [38517556825](https://github.com/lly8666/wbd-next/actions/runs/38517556825) attempt1，SOURCE即`8ce2224a734d45490c66b582f53057f1bfd40ae2`：ARM build115699659948、Windows build115699659556、ARM consume115699825062、Windows consume115699825141均**success**。

**真实范围**：Rust1.85.1 on Ubuntu24.04 x64交叉编译 `wbd-engine` sentinel cdylib和`wbd-platform` rlib；目标C11编译 `WbdAbiInfoV1=24B`、`WbdAbiConfigV1=16B`、opaque tokens=8B的sizeof/alignof/offsetof静态断言，并真实把五个API引用链接为跨目标C可执行文件。独立consumer校验SOURCE/input及三产物SHA256+size，ELF64 AArch64 machine183 / PE32+ AMD64 machine0x8664，查阅 `.so/.dll`确实导出 `abi_query/engine_open/engine_close/lane_open/lane_close` 五个 R0 符号。详情和每个SHA见`docs/evidence/M0/R0-cross-abi.json`。

**Artifacts**：ARM build id11872133561 digest939dd2c5116d603311b89579905b0d12e29ddef7e47fde0569a60ca1c4330e15、result id11871754041 digest19fce745ac881d058d827bb806826ea9fe809c91e07a33f53b8c1ed1b6bf3734；Windows build id11871923790 digest256e0e28347a40efce1225e2eca23649648aff59d57f5f4452896fda6a2ac8b3、result id11871374112 digestdf9f8b6968f7ac429d57655427fa3ce2df79097144e4861f90a9e81995f0074b；artifact zip SHA由GitHub报告，consumer校验内部文件，zip未独立下载。

**同SOURCE治理**：Governance [38517556771](https://github.com/lly8666/wbd-next/actions/runs/38517556771) completed success。上一源码`148202e0`上的native ABI回归38517436496 success、Governance38517436504 success；严格分清不同SOURCE，不能拼成跨架构性能或产品证据。

**资格结论**：`CROSS_BUILD_PASS`只说明二进制/链接/布局和符号，**Windows x64与ARM64目标系统均未执行程序**，未执行这些目标上的Go/cgo、系统IO、FakeTCP、真实业务或物理机器；不存在真实Rust steady dataplane，ABI的V4功能位始终0，Go控制生产V4继续关。R0总体partial，M1–M4继续reserved。

**唯一下一动作**：在R0引入独立wbd-codec最小WBC4 control bundle与WBG4 Game envelope、严格显式offset编码/解码、golden/未知type/重复receipt/flags/长度/边界反例，编译一次、Actions消费复用；此测试不能声称Game/receipt业务数据面已经实现。
