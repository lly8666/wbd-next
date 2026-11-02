# PLAN027A H972｜只用H971一次构建产物，Normal MSS优先再复用七场景

旧H968[41480121662](https://github.com/lly8666/wbd-next/actions/runs/41480121662) Linux装配失败、H969[41480968817](https://github.com/lly8666/wbd-next/actions/runs/41480968817)正确fail-closed。H970–H971修单份manifest源装配器，正在一次完整本地Windows/Linux原生编译[41482859398](https://github.com/lly8666/wbd-next/actions/runs/41482859398)。H972单独one-shot工作流只等待这个run **整单SUCCESS**，核对SHA、Windows exe/DLL与Linux二进制产物，然后先跑Normal外层默认1460的真实SYN/SYNACK TCP options双方1420、record/OS双方planned/applied/Stop；**真通过后**再派发唯一显式1500 Normal和Fixed/Auto/Game2/Game4及FEC六个默认1460原生最小场景，全部通过既有prebuilt跳过编译安全门。其他历史FAIL保留，异侧物理限制仍缺独立负例。

```feature-impact
{"kind":"none","ids":[],"reason":"Only narrow one-shot signed native qualifications on existing H971 product source, no product changes or false status promotion."}
```
