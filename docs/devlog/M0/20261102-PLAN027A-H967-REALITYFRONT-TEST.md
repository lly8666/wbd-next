# PLAN027A H967｜清理原Go Realityfront 单测遗留MSS引用

H966源码锁定总入口 [41478184185](https://github.com/lly8666/wbd-next/actions/runs/41478184185) 的 Windows Go 正式产品、FakeTCP真实SYN/SYNACK字节编译PASS，但 `go test -c ./internal/realityfront` 在原Go `tls_test.go:246`、`wire_qualification_test.go:128,147` 因已移除生产`faketcp.DefaultMSS`无法编译。继续不恢复生产固定1360、无legacy/modern开关。

H967分别覆盖原Go两份历史`_test.go`，用测试预设`PublicV4AdvertisedMSS()`取代旧符号，另以**仅Go测试编译**的`v4_public_mss_test.go`明确安装 Rust 对应默认outer1460→MSS1420，测试MSS值不会编译进客户端和服务端。两份manifest增加相同源锁三操作，M4历史SHA冻结保持不变，仅当前准确54操作审核。新SOURCE真实MSS/record/TUN仍NOT_RUN，H958 DF失败等均保留。

```feature-impact
{"kind":"none","ids":[],"reason":"Only restore original-Go historical Realityfront _test.go compilation against current MSS API; no product MSS or feature status change."}
```
