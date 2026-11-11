# PLAN028 M0 H1600｜H1599未进入Action场景的标题表达式错误

本次用明确正式路径取证：H1599 SOURCE`798762d9c3111b36aa0945fa199e21873abd7099` GitHub native workflow trigger实际创建为`43027647645`，状态**FAIL_PRE_WORKFLOW**，而没有运行任何原生网络测试。问题是H1599只想显示本场`outer=default1460`而增加的一段`run-name`表达式在`h1566`分支已有双右括号之后，又为H1596补了一个额外右括号；数括号13开14闭，致GitHub校验失败。仅改为13开13闭，测试新源添加括号平衡与H1596 run name标签检查；产品源码、Windows默认MTU、原Go/Rust/驱动均不变。

H1596 SOURCE496309原已跑的不同安装/同账号双OS自动/32及40UDP早期PASS、150s因为test-only pace0.6违反真实发生器min0.65而FAIL记录**保留**。H1597已经修到0.7并治理SUCCESS。本H1600在上一场早已结束且H1599实际上根本没运行网络后，提交唯一`[plan028-h1596-same-account-win-linux-150s]`，应只出一场真Windows signed Wintun + Linux4 server原TLS/Rust 150s，完整业务未出结果前 NOT_RUN。用户排除多个Wintun场景继续有效，不派多Wintun。

```feature-impact
{"kind":"none","reason":"Corrects only GitHub Action run-name expression validation and adds test source balance check; H1596 genuine scene selector unchanged, product default and protocol unchanged."}
```
