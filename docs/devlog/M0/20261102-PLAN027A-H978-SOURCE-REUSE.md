# PLAN027A H978｜用H977现行同源码构建启动仅一轮小矩阵

H977 [41485242975](https://github.com/lly8666/wbd-next/actions/runs/41485242975) 在精确原Go文件text-only测试覆盖修复后运行完整Windows/Linux源编译+历史legacy1400原生基线。H978不启动第二次构建，必须先核对H977整run成功、Windows exe DLL和Linux二进制源与SHA，以及全部Go/Rust生产源未变；先仅默认1460 Normal真实SYN/SYNACK和对端真实TCP options 1420/1420、physical/route/record与双端OS真实inner 1389（无其他限制）及Stop；整条Native PASS后，原二进制复用检查其余一个1500 Normal与六个默认1460模式的真实长度及Stop。与当前源码无关的旧Action FAIL、DF、ARM64不可移为新源通过。另补真实非对称路径收窄用例时明确原因。

```feature-impact
{"kind":"none","ids":[],"reason":"New source-locked prebuilt-only MSS native dispatcher on exact H977 binary after full success, no product changes and no premature PASS."}
```
