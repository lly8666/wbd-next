# PLAN029 H1833｜H1832第一失败为未更新的4项精确overlay result_blob

- H1832新SOURCE `70b70826df0e0a4543a8bbc02192fbc84fbb5ede` 功能卡/治理 Action43586793257 PASS，但[完整Windows/Linux预检43586793272](https://github.com/lly8666/wbd-next/actions/runs/43586793272)在`prepare_windows_wiring.py --check-only`首个失败：`assembly blob mismatch: r0/go_overlay/cmd/wbd-client/m0_native_v4_dispatch_windows.go`，先前单独H1661 Go/Windows编译Action43586793250同门槛失败。未触达真实Windows网、不可归因Direct/DNS工作负载。失败保留，无重派H1831。
- 根因：H1832 4个新`r0/go_overlay/cmd/wbd-client/` Go文件各自是`kind:create`的精确字节产物，manifest旧`result_blob`仍指旧文件；此前已更新manifest三个`kind:replace`的原Go/GUI结果，但忽略另外4个overlay源。现在逐项更新它们为git正式source blob hash：`cmd/wbd-client/m0_native_v4_dispatch_windows.go, cmd/wbd-client/m0_native_v4_windows.go, cmd/wbd-client/m0_plan029_cold_split_windows.go, cmd/wbd-client/m0_plan029_cold_split_windows_test.go`。只改receipt hash，不放宽`assemble.py`任何检查，不改产品字节/GUI/认证/规则。
- H1833本次产物校验、Windows Go/WinForms、源锁GUI实际起网、D3/慢fsync/Stop测试在提交时**NOT_RUN**；以新source自动Action收编译结果。H1831 SOURCE268的签名D3 CN多A FakeIP Direct UDP owned Stop原PASS_SCOPED仍有效；Game4 CN/IPv6/P1+P2/低延迟及完整GUI交付仍OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Only correct exact manifest result blob receipts for four already-committed original-Go overlay create files; no product or public configuration semantics changed."}
```
