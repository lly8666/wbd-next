# PLAN029 H2000｜H1999 首个 FAIL 是旧断言不容 mode3；只修测量入口、保留原FAIL

- 原 H1999 SOURCE `412bef6a2431f882aea37a74bcef57e10ce43714` [Action43858589556](https://github.com/lly8666/wbd-next/actions/runs/43858589556) **failure** 于 cheap 原生预检的 `test_h1785_guest_cache_mode_is_explicit_wsl_argv_not_parent_env`；旧静态断言只接受原guest模式 `0/1/2`，而新签名 Direct UDP RTT 测试独立显式 `3`，**真实 Windows/WSL2 网络与 Stop NOT_RUN**，不得将它当产品网络失败/成功。
- H2000 只调整这条单测的源码匹配约束：0/1/2 的 CN cache/multiA 语义和 guest mode 仍按 argv，并新增签名 `p029_udp_rtt` 显式选择3、禁止继承Windows父进程的DNS cache环境。实际 H1745 Windows/WSL2 Python业务代码、Go/Rust/Defender/MTU/Stop不动。
- 再以本新 SOURCE 原workflow的**一个**`[plan029-v3-real-direct-udp] [plan029-h1999-direct-udp-rtt]`启动原生唯一UDP场景，仍须真实720个 96/512/1200B UDP逐包回声与双方 Stop，具体结果**NOT_RUN等待Action**。H1998 4MiB原Action仍在途，无重复发起。
```feature-impact
{"kind":"none","ids":[],"reason":"H2000 repair stale H1785 pure static source assertions after adding explicit signed-only guest mode3; original native failure preserved and no product code changes."}
```
