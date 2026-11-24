# M0 main 2026-11-22 · 长期红 Actions 恢复：治理热入口、Normal/Fixed 原 Go 原生

## 权威来源与最终重验

- 任务只改原治理 prompt、原生原 Go 编排/测试专用夹具；GoTLS/Rust 产品默认、用户外层 MSS/MTU、网络/Stop逻辑**未因修 CI 而降低**。
- main governance 历史错误：追加长 PLAN029 施工文字后 `M0 read_set=33821 > 32768`，旧 Action 真红。提交 `a7c574e6293fcdb59008630236f5d5919f1a994e` 把详细施工移回 [029 方案](../decisions/M0-PLAN029-THROUGHPUT.md)，永久 prompt 仅保短入口，原 32KiB 上限未放宽。[治理 SUCCESS](https://github.com/lly8666/wbd-next/actions/runs/45027523911) 与 [治理维护 SUCCESS](https://github.com/lly8666/wbd-next/actions/runs/45027523915)。
- 长期 Native Normal/Fixed 红：原测试文件 `faketcp.PublicV4AdvertisedMSS` 未定义，因为旧工作流只复制 realityfront overlay，却没安装已存在的 [manifest SHA 检查 FakeTCP installer](../../tools/m0_install_public_faketcp.py)；最初 Fix `5574a3ca474951deddf0497ebf44d1be3645c315` 在两个工作流都调用 `--check-only` +真实安装 + exact package test，原原始 Go ref 仍为 `a7a82db31fe736ffedee330795a3234d358f1984`。原先 FEC FIXED 还缺 `tls.go` 与测试 TLS `RootCAs`字段。
- 第一次原生复跑推进后，确证新错误：旧 frozen donor `tls_test.go` / `wire_qualification_test.go`仍使用已移除的 `faketcp.DefaultMSS`；固定产品内核测试主动 panic“Rust local V4 SYN MSS not installed before handshake”。不能给 production 假装补回默认1360。
- 正式复用 [现有 H984 1460-outside/MSS1420 **测试专用** 夹具](../../tools/m0_prepare_original_go_mss_test_fixtures.py)，更新识别：当前 overlay `bridge_v4_probe_linux_test.go` 已经有 **7 个动态 `PublicV4AdvertisedMSS()` 调用、0 个旧 DefaultMSS**，原冻结 `tls_test.go` 1个、`wire_qualification_test.go` 2个仍需测试替换/初始化。拒绝未知额外引用；只在 ephemeral old Go checkout的 `*_test.go` 改造，自动生成 `m0_current_v4_mss_fixture_test.go` `init()` 安装测试 MSS1420。重复私造的临时兼容脚本已从 main 删除。Fixed 现在同批复制原有 `r0/go_overlay/internal/realityfront/tls.go`，修复 `ClientConfig.RootCAs`，仍经过真实原生执行而非跳过测试。
- 关键源 SHA：`db05cd2aee4facc314c9291f0c091c981d65ac7b` 为以上正式产品和夹具组合（后继 `a603ae6b2d43685eb326219d9682f2c41543bbde` 仅修一条旧 H984 单元断言，反映新版 bridge 动态调用）。**实际原生** [Normal Action 45029129816](https://github.com/lly8666/wbd-next/actions/runs/45029129816) `everyday=SUCCESS`；[Fixed Action 45029129860](https://github.com/lly8666/wbd-next/actions/runs/45029129860) `native=SUCCESS`。最终静态 [canonical MSS preflight 45029200958](https://github.com/lly8666/wbd-next/actions/runs/45029200958) SUCCESS；最终 [governance 45029200878](https://github.com/lly8666/wbd-next/actions/runs/45029200878) 与 [maintenance 45029200848](https://github.com/lly8666/wbd-next/actions/runs/45029200848) SUCCESS。
- 原始红 Actions不改写：`45028559904`/`45028559905`、`45028861948`/`45028862035`、`45029129838` 均保留其实际第一失败；历史 status 不随修复新 Action 变绿。

## 范围

此记录严格证明上述 **两个 main 原生工作流+治理** 已在其对应源码验证通过；PLAN012 或其他工作流不能由本记录自动等价判 PASS。PLAN029 Windows 真实三机吞吐施工另在 [PR #68](https://github.com/lly8666/wbd-next/pull/68)，其 H2312 单变量实验不会因此被晋级默认。
