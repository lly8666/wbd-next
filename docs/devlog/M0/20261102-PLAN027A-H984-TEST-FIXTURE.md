# PLAN027A H984｜H983源修正后，只修四份过时Go测试的DefaultMSS编译失败

[H983 PLAN012原生Action #41502753626](https://github.com/lly8666/wbd-next/actions/runs/41502753626) 的实时日志确认：**完整七文件实际原Go MSS装配已完成、`go test -count=1 ./internal/faketcp` 已PASS**（`H983_PLAN012_SEVEN_FILE_CURRENT_MSS_TRUE_BYTE_SOURCE_PASS`）。随后`realityfront`的四份旧测试源码仍引用当前正式V4已经删除的`faketcp.DefaultMSS`，编译失败；新产品并未实际运行。保留H983 FAIL，不冒充原生PASS。

H984只在immutable原Go Actions staging checkout迁移`admission_v4_test.go`(1)、`bridge_v4_probe_linux_test.go`(7)、`tls_test.go`(1)、`wire_qualification_test.go`(2)共**11处测试引用**到显式仅测试向量`m0CurrentV4MSSFixture=1420`（对应默认outer1460），并只在Go `_test.go` 中初始化FakeTCP test owner；所有非测试Go/Rust/ABI/MTU路径不改，不重引入DefaultMSS符号，也不增版本兼容开关。旧测试引用/文件数变更就FAIL，禁止批量替换其他目录或未知代码。

本次原生PLAN012仍待Actions真实验收，若仍有首错按实际包和日志继续修；H981/H982 Windows及两Linux已通过五+五场景不用重跑。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix only old Go test source references to a known 1460-outer/1420-MSS unit vector in ephemeral pinned checkout; current V4 product SYN byte source and Rust budget unchanged."}
```
