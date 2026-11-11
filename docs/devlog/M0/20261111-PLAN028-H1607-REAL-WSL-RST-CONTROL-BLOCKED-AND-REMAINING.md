# PLAN028 M0 H1607｜新镜像成功但 WSL 内核 RST 前置控制超时；停止同族重复测试

2026-11-11，最新运行源码 `c3a4690782a84df167fc496d61f2fe02979b2d7e`。H1606 唯一近inner-MTU Windows一Wintun+Linux四TUN Action [43042125895](https://github.com/lly8666/wbd-next/actions/runs/43042125895) **整体FAIL**，native Job `130598171269` FAIL。精准第一个失败是 `Launch actual WSL2 Linux and direct full public two-OS product` 的**Linux 内核 underlay FakeTCP RST 规则准备**：`WL_WSL2_COMMAND_TIMEOUT seconds=120 binary=wsl.exe`，随后抛 `Linux kernel underlay RST control unavailable`。尚未启动原Go credential TLS、Rust M4、Windows Wintun OS配置或发送近MTU应用 UDP。原20次近MTU回声与六owner业务Stop全部 **NOT_RUN**，不是产品损坏或通过。

对比 H1605 [43040746444](https://github.com/lly8666/wbd-next/actions/runs/43040746444)：原入口`releases.ubuntu.com`无法解析，H1606单次官方Ubuntu镜像回退被**实际触发**；下载的24.04.5 WSL rootfs仍走canonical精确SHA256 `bb415d824822c4b878125729af451a5d18fb13d1cf5cbed9a7393ad64ac6039e`，WSL image import成功，真实guest内核探针`PASS_GENUINE_WSL2_GUEST_PRECONDITION_ONLY`。但后续Wsl.exe再次卡120s，因此不能将“镜像下载已修好”外推为完整宿主可用于本轮产品验收。

网络业务前的**真实正向**：Linux x86_64 original-Go TLS client/server + Rust ISA-L构件由成功 SOURCE `8a31375e` 原真实Action `43027983611`下载，产品源码从8a313至c3a `crates/r0/Cargo/prepare_windows_wiring`零差异，逐实体本地SHA及CI manifest核验成功；Windows signed Npcap1.88安装通过、Go EXE/Rust DLL sha复用且FEC`native_fec_acceleration=true`，最终Npcap精确清理 `WBD_NPCAP_DRIVER_CI_CLEANUP_PASS`。**没有Wintun实际业务owner可供Stop**，不得用Npcap cleanup冒充Wintun WAL Stop。

原始 artifacts 与逐文件SHA均已读取：
- artifact `13866116591` ZIP SHA256 `5647a1261914fb322a33ea5dfa4501d2464dbad17d6b66e84924f`：`wsl2-real-guest-probe.json` result PASS_PRECONDITION_ONLY, `product:NOT_RUN`；另原 `wsl-import.log` 成功；
- artifact `13866761087` ZIP SHA256 `8206909df6cf7dedf85da108c724ee5a4deca4501d2464dbad17d6b66e84924f`：仅Npcap clean、Windows VM指纹、Windows binary manifest；**没有 strict-native-report**。全场 stdout 原始 Action 保留；
- 同源治理 `43042125801` + 维护 `43042125943` **SUCCESS**。原更早Ubuntu apt DNS失败`43034982111/43035399302/43035735021`、H1605 image DNS失败`43040746444`仍保留原FAIL。

**现场停止策略**：已尝试明确区分不同外因（apt源DNS→原构件SHA复用、rootfs DNS→官方同hash镜像一次回退），问题已转移到hosted WSL内核命令120s无响应。受用户要求节制Actions和原生硬门，**不再在同一类Windows hosted Runner复派近MTU**、不跳过FakeTCP RST或改产品预算刷绿。H1601同账号5端真150s以及H1604生命周期仍按各自精确SOURCE有效；近MTU窗口为`ENVIRONMENT_BLOCKED_NOT_RUN`，如要完成，需要新的可靠Windows DUT/WSL环境而不是更多seed。用户明确排除多Wintun，H1587旧route/WAL FAIL保留未支持限制。

[H1607 source-locked evidence](../../evidence/M0/PLAN028-H1607-SOURCEC3A-WIN-WSL-RST-CONTROL-TIMEOUT-NOTRUN-20261111.json)。028仍IN_PROGRESS。已知Windows L3独立控制设备缺失（H1450），旧ARM64两条1800s只复用未改组件，不擅自发新的物理实验。

```feature-impact
{"kind":"none","reason":"Only reconcile exact current Action environmental failure and original artifact hashes; no shipping product, default or feature change."}
```
