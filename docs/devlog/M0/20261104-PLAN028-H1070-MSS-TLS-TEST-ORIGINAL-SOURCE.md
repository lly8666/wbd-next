# PLAN028 H1070｜测试常量与原 Go 装配对齐，Windows/Linux 单位纠错

H1069 [x86标准TLS Action41690252398](https://github.com/lly8666/wbd-next/actions/runs/41690252398) 仍未到真正测试：旧 `m0_prepare_original_go_mss_test_fixtures.py` 对原捐赠仓库 `tls_test.go` 要求恰好一个被删除的 `DefaultMSS`，但现行 manifest 早已用新 `tls_test.go` 覆盖，该源码是0个。测试夹具不应盲目复用不适配原 manifest 的全包旧版本迁移。

共同根因是 `r0/.../admission_v4_test.go` 唯一测试预期仍引用已删除 `faketcp.DefaultMSS`。用原项目既已批准 `outer=1460 → MSS=1420` 的**静态测试断言**替代，更新原 Go manifest 的精确 test result blob，使 Windows Go 单测也不需要额外兼容 shim。保留修改到原供体旧 `tls_test.go` 的迁移脚本，但把已消除旧符号的 AdmissionV4 测试从 EXPECTED 明细中剔除；这是迁移脚本的正确源映射而非放宽匹配。新标准TLS Action 只安装源码/两条 TestV4 的必要文件，不再调用与现行 manifest 冲突的旧迁移脚本。

全程产品端 TLS/FakeTCP/Rust/Wintun/FEC/Game 数据面**未变**；源锁和测试有且仅有一个 H1070 新SOURCE，不能把此前有旧行为的测试标 PASS。前面 H1069 治理 Action41690252417 SUCCESS，与TLS真实外观独立。Linux任务仍是 x86双端，下一独立任务原生ARM64双端。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1070 fix exact original-Go V4 admission test removed-MSS reference and manifest; maintain real TLS redline pending native wire, no product state change."}
```
