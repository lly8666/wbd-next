# PLAN029 H1900｜修H1898签名场景前旧H1896持续UDP静默测试契约

- [H1899 Action43688459805](https://github.com/lly8666/wbd-next/actions/runs/43688459805) 首错在Cheap Python H1896静态`test_signed_original_p2_and_30s_per_phase_tunnel_contract`，源测试写死`if total%128==0 and not SUSTAIN:`，而新H1898还应防高率场景每128包打印日志干扰CPU，所以源已收紧成`not (SUSTAIN or HIGH_RATE)`。上一H1894高精钟assert修复已经通过。**真Windows原产品、签名Wintun/WSL2高率场景尚未运行**，不能将静态拒绝称为TCP/UDP退化。
- 只将H1896静态测试升级为同时断言两场大负载都不逐128包输出，并保持`MAX_SUSTAIN=3200`普通、`9000`持续、`14000`目标高率以及WSL guest**显式**环境传播。`GetProcessTimes`与单Windows QPC、原30s/SHA/FIN/Stop测试原约束未放宽；H1898 500Mb/s单向/700Mb/s双向目标、512+256+256MiB、无新产品线程和原代码保持未变。
- H1898已通过[治理和功能卡](https://github.com/lly8666/wbd-next/actions/runs/43688298677)；上轮H1897超14字节的热读预算已通过缩短cursor修复，没有调阈值。H1900仍必须跑真Windows2025/WSL2、96B持续Tunnel UDP每窗p99、CPU独立取样和双owned Stop，仍NOT_RUN。实际低于500/700以真实值记录，不冒充通过性能门；P1/P2仍OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"H1900 updates only stale H1896 silent-UDP static source contract for both capped sustained and 500/700 high-rate target scenes; no production or feature-card change."}
```
