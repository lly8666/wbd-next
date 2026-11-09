# PLAN028 H1481｜H1480 YAML解析失败，未运行原生网络；修正源文件而非重测

初次新源码 `5f10af69a682c6735220b0e256bae936589c1b51` 的 [Action42623129084](https://github.com/lly8666/wbd-next/actions/runs/42623129084) conclusion=FAILURE，**jobs空列表**、无任何编译/Go/Rust测试、原生ARM64业务未运行，归类 `HARNESS_OR_CI_FAILURE / NOT_RUN`，绝非产品FAIL或条件修复NOT_TRIGGERED。查源文件 H1480工作流第98行嵌入Go regex `...$'` 后被JS字符串replace解释为特殊后缀替换，复制整段旧构建导致重复脚本和无效YAML；不是产品构建或客户端/服务端协议问题。

只修 `.github/workflows/m0-plan028-h1480-arm64-client-ready-fence.yml`：从已有正常 H1389 ARM64构建模板重建一次，使用替换回调保留Go测试regex原 `$`，核207行、build/scene各一、两个同manifest构建产物上下游名相同、原始18xx线路改为单180s rotating12、两端原生ARM64/五client/实Stop、有条件闸真触发和全部唯一UDP零缺失作为严格门。未更改Go/Rust源码/发包/缓冲，不开新场景或种子；自动push只触发这一个新工作流。源锁后需重新核真正commit SHA，当前候选验证仍NOT_RUN。

以前原始H1478十缺包失败和114967外层全部匹配证据完整保留；PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Only workflow YAML syntax repair after preparse-only CI error."}
```
