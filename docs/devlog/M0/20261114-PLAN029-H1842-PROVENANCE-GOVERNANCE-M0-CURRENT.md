# PLAN029 H1842 | 来源一致性治理修复，保留签名H1841独立运行

- H1841 `b7e947a8ede357e6e7c0459db2a85bf61eae7e41` [真实产品Normal CN签名Action43597050204](https://github.com/lly8666/wbd-next/actions/runs/43597050204) 已启动、仍待真实网络和owned Stop终态。本H1842无[plan029-real-product-cn]标签，也不修改`m0_wl_public_normal_e2e.py`，不得重复派发同一签名网络场景。
- 治理 Action43597050242/maintenance43597050222 首个结构错误 `evidence is for a different SOURCE`：cursor的`last_tested_source=a50f8c5`，H1839真实P2引用source a50是恰当的；H1840前置MTU拒绝引用的是另一真实源`82585c6`，**不应**作为同一测试SOURCE的证据。现将H1839保留在唯一`evidence_refs`，H1840转为`context_refs`，保持两项真实记录，不改变`tools/governance.py`的逐SOURCE校验。
- maintenance另一错误：H1837添加装配器GUI/CLI清单一体化契约后`r0/go_overlay/assembly/assemble.py`当前Git blob为`31da7dd474f91010b02bfb7c6648334270bd2ed1`，`tests/test_m4_frozen_windows_main_import.py`里的**M0_PLAN029_REVIEWED_CURRENT**尚指向`2bbb6b5...`。H1842同步当前已审核派生SHA，仅更新一个M0 current mapping，不碰`PINNED_FILES`冻结M4的历史blob、旧Go donor或manifest原件；原历史审查不可回写。
- 不改Direct TCP调度、路由、WAL或性能数据：H1839真P2已证实普通物理1MiB=297ms，Direct 1MiB上传18969ms，首回包约21172ms，38s只收917504B；Rust回程`to_inner=65536`积压，Tunnel小UDP至少2432次回显。根因需kernel ACK/window段证据，不能靠10ms变1ms、胡乱加buffer解决。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct M0 cursor source-bound evidence refs and explicitly reviewed current assembler SHA; preserve historical M4 SHA and independently running H1841 signed test."}
```
