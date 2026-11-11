# PLAN028 M0 H1598｜保留同账号早期真实原生成功、150s非法pace失败，0.7唯一复验

2026-11-11，前次 H1596 SOURCE`49630902` Action [43024873684](https://github.com/lly8666/wbd-next/actions/runs/43024873684) **整体FAIL**，不是产品TLS/租约/驱动失败。原生Job`130539482919`原artifact`13857197465` ZIP SHA256`8dd77f2776abf360c5ae5a69698f41ed6948b504ca2c6bd89cbb815d2c752afc`、严格报告SHA256`7077c9834ac835f575c3c276e8948fbaaf7781dce6181a4c319a3f334486591d`。真正首错`H1574 native app exited before real 150s server`：前版本测试选`scale=0.6`低于原`tools/m0_plan028_h1548_mixed_os_app.py`已有`0.65<=scale<=1.35`界限，造成发生器自己退出，后段150s业务未完成。没有证据表明该早退是产品故障；不删除原失败，不写150s PASS。

有效局部事实：同一用户Alice凭据由Windows签名Wintun自动选`10.66.0.132/32`、Rust AES256 cipher3，独立Linux Bob原Go安装文件同账号得`10.66.0.173/32`真OS TUN，其他三Linux也各自OS Ready；五端真正UDP echo 40次全部通过，Win客户端WAL/原Rust Stop正确，netem/WSL桥恢复。详细精确平台、SOURCE/binary hash见[H1598 evidence](../../evidence/M0/PLAN028-H1598-SOURCE496309-SAME-ACCOUNT-EARLY-OS-FAIL-FIXTURE-20261111.json)。

H1597 SOURCE`7f84a518`只把测试夹具/CI强度改0.7，保留原真实发生器安全门，已源级/治理通过（Actions43025487562/43025487403）。旧Action已经终结才使用新提交标记`[plan028-h1596-same-account-win-linux-150s]`触发**唯一**一场完整修复复验，仍是一Windows Wintun+Linux四TUN，同账号双安装、150s双向UDP/TCP/Win Stop后Bob存活/六owner Stop；没跑第二个Windows Wintun。未收到新场原始报告前仍NOT_RUN。

```feature-impact
{"kind":"none","reason":"Source locked negative run classified from raw failure evidence; add native generator bound source assertion and launch only one corrected test; no product feature/behavior/default modified."}
```
