# PLAN029 H1990｜WinSock分片轮换Rust真PASS，修历史H1940严格源码检查

- H1989 SOURCE `e1bc78c192bbca3b045e8e1339f032211aab626d` 的 [Rust组件Action43833451089](https://github.com/lly8666/wbd-next/actions/runs/43833451089) **success**：原 Win2025 job133184130063 新 `plan029_wait_any_rotates_all_sixteen_tcp_shards_no_cross_flow_hol` 在 104/106 验证中各PASS，Ubuntu133184130295 PASS。[原M0预检43833451125](https://github.com/lly8666/wbd-next/actions/runs/43833451125) cheap/Linux Rust/Windows Rust编译测试成功，Win Rust job133184432009 同新测试 `ok`，收件时 Windows Go job133184432000 尚在途；无新 p99/CPU 每GiB实测。
- [H1989治理Action43833451163](https://github.com/lly8666/wbd-next/actions/runs/43833451163) **FAIL**：FeatureCatalog job133184131787 第一异常是 H1940历史源码断言要求不再存在的逐字 `let (order,n)=native_tx_wait_order(...)` 及其紧邻单行phase更新；Governance job133184132117 SUCCESS。不是WinSock函数编译失败，更不是联网/尾延迟PASS。旧FAIL保留。
- H1990 只在 `tests/test_m0_plan029_h1940_tcp_event_fair_wait.py` 改两处历史字符串断言为**更严格**的新合约：`mut order`、唯一原 TX `rotate_tcp_shard_wait_order`、真实shard完成后head=(last+1)%16、Stop index0、三类优先轮换、16-shard全覆盖、纯Tunnel仍3 handles、单次 `io::wait_ready`、原进展tickets完整保留。实现代码/性能开关/驱动/Firewall/MTU本批不改。
- H1988旧SOURCE [M0 Action43832554963](https://github.com/lly8666/wbd-next/actions/runs/43832554963) 的`native-public-two-os` job133183275348在途，**不重复dispatch**，后续按原失败/业务凭据如实收件。本轮不再扩极端饱和、CDN反例和2048旧探针。H1974真实61ms仍 OPEN，P2/CPU需要同VM正常A/B才能叫收益。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H1990 preserve original H1989 static FAIL but strengthen old H1940 source contract for exact WinSock 16-shard round-robin and Stop/Tunnel priority; real Win2025 Rust unit PASS and performance still unmeasured."}
```
