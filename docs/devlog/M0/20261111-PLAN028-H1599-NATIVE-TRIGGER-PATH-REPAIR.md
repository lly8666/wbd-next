# PLAN028 M0 H1599｜修新源测试触发路径，真正派发唯一合法0.7跨OS同账号场

H1598文档/evidence修订完成后未产生`M0-WIN-LINUX` Action，核现行`.github/workflows/m0-wl-public-normal-full.yml`发现`on.push.paths`列了旧H1581静态测试，却**漏新H1596测试文件**，纯docs变动无法运行真实场。于是本提交在已有触发名单补`tests/test_m0_plan028_h1596_same_account_cross_os_scope.py`，只对新H1596场修`run-name`显示的`outer=legacy1400`为真实产品默认`default1460`，并带唯一`[plan028-h1596-same-account-win-linux-150s]`选择标记。

SOURCE496309 Action43024873684完整150s前失败是测试发生器0.6<原限0.65，真实原TLS/Rust及Window+Linux Bob同账号各自不同自动/32与先导40 UDP均成功，原报表FAIL保留。修复SOURCE7f84现在test-only pace0.7合法且六端应用效果必读回，正常产品参数未变。此提交**首次真正触发修正版**单Wintun+Linux4独立真实150s验证；不并行派另一场、不运行双Wintun。后置资格严格要求整150秒双向UDP/TCP、Windows退出后Bob仍收发和六owner Stop。没有最终Action时不能提前写PASS。

```feature-impact
{"kind":"none","reason":"Only repairs existing workflow push.paths to include the current same-account crossOS source test and corrects run-name MTU labeling for its scenario; no product feature/default change."}
```
