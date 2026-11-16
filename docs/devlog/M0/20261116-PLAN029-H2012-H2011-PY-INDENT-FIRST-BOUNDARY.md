# PLAN029 H2012｜H2011预检 Python 缩进两行修正
- 首个H2010 [Action43881026543](https://github.com/lly8666/wbd-next/actions/runs/43881026543) **FAIL** 于静态旧cleanup断言，H2011 `c0eddf3` 尝试修断言却产生新测试文件的 **IndentationError**：[Action43881781330](https://github.com/lly8666/wbd-next/actions/runs/43881781330) cheap失败、[治理43881781341](https://github.com/lly8666/wbd-next/actions/runs/43881781341) 同一原因FAIL；原真实Windows/WSL2共享CDN **NOT_RUN**。
- 本次只将新增的两处断言缩进与 `self.assertIn` 原级对齐，保留完整新旧进程资源cleanup证据、原外部两个脚本/业务/Windows路由不动；仍只触发一个原Normal CDN+TCP53+no fallback合同验收。
```feature-impact
{"kind":"none","ids":[],"reason":"H2012 fixes test-only indentation from H2011 first cheap boundary, no product or native fixture logic changes."}
```
