# PLAN029 H1754｜H1753真实Defender工作流0-job首错（YAML配置）

- H1753 SOURCE `7e952f3bd257037af20183c14d1a3be6f65e957d` [Win原生Defender流程43437134221](https://github.com/lly8666/wbd-next/actions/runs/43437134221) **FAIL_CONFIG_PRE_JOB**，jobs=[]，并非Defender COM失败或原签名Wintun联网失败。三个其它自动Actions也因同一源YAML格式无效未启动。
- 直接原因：生成workflow字符串的JavaScript`String.replace`使用替换字符串，PowerShell内部的Go`-run '^Test...$'`包含特殊`$'`，触发“插入原源剩余字符串”扩展，导致原`upload-artifact`重复且内容截断。H1752原来正确的工作流仍可独立获取。
- H1754直接从**已通过的H1752工作流**恢复，使用替换回调而非字符串替换，确认1个精确真实COM单规则CI步骤、1个归属报告、1个artifact上传；其Go测试文件和原native COM实现未变。
- H1753 failed Action不能转成PASS；H1754 Windows2025原生COM实际Add/Readback/CAS Remove、governance结果待新SOURCE。继续仅针对这项真实首错，不复跑历史矩阵；完整kernel Direct TCP后续仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Repair malformed H1753 CI YAML before jobs by rebuilding from H1752 known-good workflow; retain failed config evidence and keep real Defender native OS test unqualified"}
```
