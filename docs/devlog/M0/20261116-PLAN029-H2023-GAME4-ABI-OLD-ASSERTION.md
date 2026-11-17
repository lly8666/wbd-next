# PLAN029 H2023｜旧H1820静态V3 ABI检查接纳新增Game4分支

- H2022 [原Action43894039520](https://github.com/lly8666/wbd-next/actions/runs/43894039520) native selector已承认Game4 CN，但cheap旧H1820源码断言只接受 `PRODUCT_SPLIT_SCENE -eq '1'){`。新合法条件同时保留原Normal V3并新增显式Game4 CN `m0_v4_probe`；该Action在实网前失败，原网络NOT_RUN。
- 仅更新测试断言同时要求原V3和Game4 V4真实FFI导出，不改产品数据面、Defender/WAL或Stop；不刷旧矩阵。
```feature-impact
{"kind":"none","ids":[],"reason":"H2023 static H1820 guard updated for original V3 plus explicit Game4 V4 ABI only."}
```
