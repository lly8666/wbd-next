# PLAN029 H2019｜原始Go单一assembly五个新Game4文件哈希与SOURCE一致

- H2018 [原Action43891626934](https://github.com/lly8666/wbd-next/actions/runs/43891626934) cheap前置 **FAIL**：`tools/prepare_windows_wiring.py --check-only` 核对`manifest-plan020-m0.json`时发现已更改的`internal/windowsownerlease/original_tls_native_product_windows.go` blob mismatch，未进入原生网络。其余四个Game4改动也需要同步。非Game4功能失败、与网络无关。
- H2019只更新原单Go overlay manifest五个`create.result_blob`为新真实Git blob SHA；未改Go业务、协议、安全门、默认mode和主manifest其他138项。原脚本强校验继续开启，不用跳过manifest来伪造Go编译/Action PASS。
```feature-impact
{"kind":"none","ids":[],"reason":"H2019 exact frozen-Go overlay manifest result_blob for five Game4 CN edited files; no product changes."}
```
