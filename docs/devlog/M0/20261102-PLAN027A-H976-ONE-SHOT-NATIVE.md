# PLAN027A H976｜H975仅一次构建，先Normal1420 MSS再七模式复用

H975原始SHA `335b25c878e8497aab143239cc8629c23826a9b9` 的Windows/WSL2双端源锁构建Action [41484325423](https://github.com/lly8666/wbd-next/actions/runs/41484325423)仍运行。H976仅新增一个监听本文件push的一次性Action；要求此原run整条SUCCESS、同source EXE/DLL/Linux产物存在、两个原Go安装器+生产源码没有漂移。先默认1460 Normal真实SYN/SYNACK TCP选项双向1420与peer decoded、record cap、Windows/Linux OS MTU 1389、真实UDP/TCP、Stop；这个Action完整SUCCESS后才派显式1500 Normal以及默认1460六种模式单独原生运行，全跳过产品编译。

H971/H972和H974旧失败原样保存，不借H948旧源PASS升级新源。非对称人工限制仍是独立NEGATIVE，无法由相同路径正例替代。

```feature-impact
{"kind":"none","ids":[],"reason":"Only exact H975 prebuilt source once-run native narrow MSS dispatcher, no product changes or unmeasured PASS."}
```
