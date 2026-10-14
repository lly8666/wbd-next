# R0 Go 控制入口实际接线与 V4 fail-closed 收据

2026-10-14。恢复前核对 remote main `c9435d49`，cursor seq7 checkpoint `f2a1c639` 之后仅一个 cursor-only H，所有既有run完成、无open PR。没有覆盖竞争写入。

**why_now**：既有Go V4握手测试仅是显式opt-in Go入口，旧`runtimeentry`仍然用V3语义的数据面。直接将`DataPlaneReady=true`暴露到 CLI 会错误广告未实现 receipt/Game，导致认证成功但无法处理V4 payload。因此第一步在真实控制调用点设置不可配置绕过的fail-closed门。

**实质S** `b1e1cf627c18674433ef45c9fc2eaf172734ebe6`：在 `r0/go_overlay/internal/runtimeentry/r0_admission_mode.go` 实现0=保留旧Go库调用行为、显式3校验policy、4因Rust能力不足拒绝、非法值拒绝；通过 `tools/r0_go_control_patch.py` 以精确旧 Git blob SHA 和唯一锚点修改 Actions 临时旧 checkout 的实际`DialTunnelClient`、`NewLifecycleServer`、两端Linux CLI入口。两个CLI新增`--admission-version`默认3，帮助说明V4不可用；`--check-config`服务端回执 `effective-admission-version=3` / `v4-capabilities=not-implemented`，凭据/route-key继续脱敏。旧Go远端仓库未写入。真正V4 epoch store / ReleaseLane 没有对应可用Rust数据面状态，所以明确不虚接，尚待ABI和生命周期实现。

**真实 Actions**：[run38512634751](https://github.com/lly8666/wbd-next/actions/runs/38512634751)，attempt1，SOURCE精确 `b1e1cf627c18674433ef45c9fc2eaf172734ebe6`，旧Go SHA `a7a82db31fe736ffedee330795a3234d358f1984`，Go1.23.12 Linux x64。build job115684380330编译一次两个Go测试二进制与两个Linux CLI；consume job115684594712验证SOURCE/输入及全部4个二进制SHA256/size后不重编译执行。六个顶层Go测试PASS（四新增实际调用入口+两个原V3真实TLS），客户端和服务端各3种不受支持/未就绪版本早期拒绝PASS，服务端真实`--check-config`PASS。build zip artifact11870551418 digest d121d89e3aba8c72b71e26e8a423019650a39099b2ae89e34aaa3daab616dc0e；result artifact11870931356 digest 8e0dcf4cb94d6c68b9fd6e152786104b86208696ced11812f1a48e62d007f14c。archive hash由GitHub提供，job内核对binary与SOURCE；未额外下载zip进行独立验证。Governance [38512634892](https://github.com/lly8666/wbd-next/actions/runs/38512634892) success，仍非产品PASS。

**done_when**：本原子已满足 Linux Go 控制真实调用点 fail-closed、参数可见、默认V3回归且Actions二进制消费通过。R0总体仍partial；M1–M4继续reserved。

**重要未做**：旧 Go CLI新二进制只在Actions组装测试，产品未发布；Windows CLI/GUI未接；V4入口不能投产，Rust receipt/Game、真实V4 epoch lease和自动释放、旧80秒风险、C/平台ABI、Windows/ARM与产品/性能/物理全部NOT_RUN。

**唯一next_action**：原生Go↔C↔Rust ABI尺寸/版本、handle generation、错误与跨语言生命周期探针；Actions真实编译运行且复用产物。借此作为未来V4 readiness的必要前置，但不因此启用V4。
