# B97｜Android Fixed/Auto M3 record budget 复用、FEC真实 source/parity、DNS TC

B96 SOURCE `bae7a69c2d47a91ea0fd3813474e8985b38a4677` [Action 45503675129](https://github.com/lly8666/wbd-next/actions/runs/45503675129) 19 SUCCESS / 1 FAIL / 6 SKIPPED；9 guest 中8 PASS，9/9 kernel_cleanup PASS。三 UID single/group/all 24/24 前后物理与双socket实际 TUN echo，5500 CN 前缀、route-get 排除与 Stop PASS（group仅主traffic UID发包，第二UID仍只查路由）。三个系统 DNS actual Resolver/owner/query/Stop/cleanup PASS；physical host、tunnel隔离 TUN、CN双路径。七原 TLS/lease/M4/Stop 7/7，Normal、Game2/4 off/fixed 双 socket 原 M4 TX 5/7 PASS。 [normal 138834727639](https://github.com/lly8666/wbd-next/actions/runs/45503675129/job/138834727639) Fixed/Auto 两种 App socket 发包成功但普通业务 RAW copy不增，FEC revision1 pending，未获 source/parity/M2。

源码直接冲突：Android Fixed M4 worker 原 `android_fixed_frame_budget` 的 FEC reservation=14；已编码 kind2/3 的共享 `seal_fec2_product_one_inner` 和 `seal_scoped_authenticated_one_padded` 明确要求 fec_overhead=0。B97 在同一原 owner 冷态从同一 physical MTU/peer MSS/record limit 派生两视图：inner fixed 保留14B，record base 仅供已编码 source/parity；三个 source/parity调用点类型按原语义（含fragment，实际两source两parity调用）修复，无 per-packet 新 budget 计算、无修改原 MTU、共享 seal/AEAD/PN/Stop 无改变。Host 新 regression 复用原 codec full-sized repair，inner=1375、wire=1420、repair payload=1389。真实Android待验证，不提前判PASS。

本轮仅3隔离 guest（Fixed、Auto、DNS physical TC）。两FEC模式独立真实 App Java/AF_INET TX，另32个真实 AF_INET UDP source（实际 native source delta>=32、parity delta>0；没有伪造 reverse M2，必须保持 mature/applied=0），失败输出原 M4 pulse 与已存在的9槽 FEC ABI。DNS 新场景真实 Android Resolver 查询 tc.wbd-b90.test，host fixture 必须有 UDP TC 及 TCP 两条实际收据；不声称 resolver TCP入口一定发生或远端数据面。8个B96 green guest 不重复，基线构建/host仍同源。B97 未运行完成，尚无 peer RAW 双向/M2 FEC recovery/READY自动重连或ARM64实体机新证据。未操作外部服务器/实体手机/main。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"B96 actual Android UID/DNS and 5/7 TX acceptance; fix Android FEC reserved inner versus encoded record budget, focus real source/parity and DNS TC guest."}
```
