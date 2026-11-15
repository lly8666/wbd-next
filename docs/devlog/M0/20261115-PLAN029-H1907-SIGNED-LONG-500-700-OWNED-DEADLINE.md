# PLAN029 H1907｜修复 10GiB 长量测试双层固定预算，保留真实场景和 Stop

## 源锁定首错（来自 H1906 真实 Action）
- [H1906 signed Windows/WSL2 Action43693416486](https://github.com/lly8666/wbd-next/actions/runs/43693416486) 精确 SOURCE `cb7339214880ceb2b113f8c3ee3d3b57441c4846` 的原始 ZIP `m0-wl-full-public-normal-direct-h1506-legacy-43693416486`：Linux原`PLAN029_H1760_LINUX_PHYSICAL_TCP_ECHO`真收32KiB、FIN及回显，Windows原`PLAN029_H1760_WINDOWS_FAKEIP_DIRECT_TCP_ECHO`亦PASS。原P2物理4MiB50.940ms、Direct4MiB109.552ms，双应用SHA、FIN完整；原产品 Rust 运行时诊断内侧累积数据量在kill前超过3.4GiB、外侧回传累积超过1.2GiB，且旧`mode-batch`打印`WL_PUBLIC_REAL_MODE_TIMEOUT mode=normal bounded_seconds=165`。高率 guest 源锁定listener READY；**长流量没完成，原Action FAILURE，Stop不合格**。
- 这说明 H1905 早期真实32KiB FIN stall 是独立历史不稳定缺口，H1906复测已消失；目前最新源码遇到的是**测试预算首错**：高率源H1903同一 VM 先物理2GiB单向500Mb/s＋双向各1.5GiB聚合700Mb/s，再Direct重复四阶段合计10GiB，物理最短142秒，还必须经过原P2小4MiB、8s pre/post纯UDP CPU基线、每个阶段最少750个96B Tunnel小包、完整Stop。旧normal 165秒无法覆盖，即使数据通路正常也被父测试脚本提前kill。
## H1907仅修原生测试生命周期，不动产品/网络
- `tools/m0_wl_public_modes_e2e.py` **只** 对`GITHUB_ACTIONS=true`＋`mode=normal`＋原V3/CN、原P2 mixed/bulk/high-rate/long四重签名源标记全满足、排除普通V2/N0/P200/ABBA/Direct压力时，将原Normal nested child`165s`覆盖为`900s`。其余模式与旧165s全不变。
- `tools/m0_wl_native_step_runner.py`同样在**原Normal真实签名源锁**下给予外层原单PID拥有者`1060s`；四段各原脚本180s的独立上限不动，900 < 1060 < 原workflow真实步骤24分钟，仍留下一次拥有者停止及准确WAL恢复工序，不允许非法场景延长。单位测试枚举必需和禁止场景，检查缺任何高率签名、V2/压力/ABBA即FAIL。
- 流量脚本每发送256MiB最多打印一次测试端应用原OS内核`sendall`接受字节数和单调时间，严格标注`remote_delivery=NOT_PROVEN_BY_SENDALL`；没有收数据伪证、无产品每packet日志、新Rust线程、系统路由、MTU、队列/FEC/crypto改动。不改2GiB/1.5GiB体量、无人工加速或放宽SHA/FIN。所有真实payload仍64KiB循环缓冲。
- [H1893 真128 Wintun](https://github.com/lly8666/wbd-next/actions/runs/43680192237)已独立PASS_SCOPED；[H1903收短500/700Mb/s](https://github.com/lly8666/wbd-next/actions/runs/43688959038)现存短量499.965/699.760实际Mb/s、96B Tunnel p99和原Go/Rust用户/进程内核CPU已签名。长量**H1907 SOURCE尚NOT_RUN**，不将父进程延长本身标成性能好坏。H1905/H1906失败保留，10GiB未有完整阶段SHA/Stop和CPU差值，P1/P2/GUIGame4/IPv6仍OPEN，PLAN029 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"H1907 only exact source-scoped signed original Windows/WSL2 LONG benchmark runner budgets and test-app bounded progress; no production networking/feature change."}
```
