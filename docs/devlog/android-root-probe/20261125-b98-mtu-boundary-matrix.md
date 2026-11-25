# B98｜原 MTU oracle 审计、7模式真实 TUN 临界数据

B97 SOURCE `94cb981fa71affb20c462f7a105310b0be3dd98d` [Action 45506419874](https://github.com/lly8666/wbd-next/actions/runs/45506419874) 14 SUCCESS/0 FAIL/6 SKIP。Fixed [138844420749](https://github.com/lly8666/wbd-next/actions/runs/45506419874/job/138844420749) source 2→34, parity 4→67；Auto [138844420731](https://github.com/lly8666/wbd-next/actions/runs/45506419874/job/138844420731) source 2→34, parity 2→34；均双 socket actual M4 TX/Stop/cleanup PASS，mature=0 applied=0（无 peer M2）；[DNS TC 138844420740](https://github.com/lly8666/wbd-next/actions/runs/45506419874/job/138844420740) actual Resolver、host UDP TC→TCP、Stop/cleanup PASS。Host b97 full MTU regression PASS；结合 B96 七模式普通 App→原 Rust RAW copied 7/7，UID 24/24，DNS三路+TC PASS。未称 remote E2E。

MTU根因对照 main 93b249e6a332fbd971c32a5db4dcd2ef1010eec2：path_budget.rs blob 8793d8b146ac50b3ec96adf0ca36533c72f4c6cf 及 path_budget_tests.rs blob e33556975fc59bbfda0723514f3988cd03bf481d 完全同一；共享 seal_fec2_product_one_inner 实现逐字相同；main 不存在 Android-only v4_android_original_m4.rs。不是共同 MTU 公式错误，而是该 Android worker 把14B reserved inner FrameBudget 交给已编码 kind2/3 的原 M3 record 接口。B97 两视图仅冷态计算，原 MTU/AEAD/PN/Stop不改；默认1460 outer→1420 record→1389/1375/1373/1358 inner。

B98 新验收 7个独立 guest，每模式 outer1280、1460、1500及1500/真实 server TLS record cap1200 四场景，共28。真实原 Go cold oracle、TLS/lease、OS TUN MTU读回，普通 App AF_INET UDP DF 在内层 MTU-1及MTU各4包，原 native RAW copied delta>=4；Normal Fixed/Auto同场实际 source delta>=4、parity delta>0且无伪造 applied；MTU+1 只接受 kernel EMSGSIZE。每场 native/UID Stop与TUN close及外部 kernel cleanup。Host执行共享原 MTU ABI全测试（包含物理/peer/header/cap等）。不改生产算法/路径，不改 main，不重跑之前UID/DNS/生命周期专项，无实体机或外部服务器。边界实验是 counter/OS/应用证据，尚无独立wire长度抓包、混合lane MSS、DF=0碎片端到端或remote M4；新SOURCE待CI。治理检查历史失败尚未修。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"Record B97 Fixed/Auto real source/parity TX and Resolver TC; audit original MTU and add seven-mode Android boundary matrix."}
```
