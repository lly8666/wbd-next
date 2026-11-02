# PLAN027A H980｜修正H979两处精确overlay blob，保持源锁硬门

H979 已修正式 Windows Fixed 入口仍使用旧FEC1 56B的问题，产品原代码3个文件已提交。首次新源Action [41493646650](https://github.com/lly8666/wbd-next/actions/runs/41493646650) 只在廉价preflight `prepare_windows_wiring.py --check-only` 失败，首错 `assembly blob mismatch: r0/go_overlay/cmd/wbd-client/m0_native_v4_unavailable_windows.go`；Go/Rust编译和原生未开始。H980只修 plan020 **两个**被改过的Go overlay `result_blob`，不改任何Windows Go/Rust产品代码、不放宽钉选。旧H978 [41488208305](https://github.com/lly8666/wbd-next/actions/runs/41488208305) green但1333语义不合格原样保存，新源Fixed真实数值仍NOT_RUN。默认1460，显式最大1500。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Track H979 source-lock failure and repin only two exact changed Windows V4 cold budget Go overlay blobs, retaining incorrect old Fixed 1333 semantic evidence."}
```
