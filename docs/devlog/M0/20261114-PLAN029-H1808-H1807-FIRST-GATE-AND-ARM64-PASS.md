# PLAN029 H1808｜ARM64 真原生通过；Windows H1807 首错为旧夹具静态断言

- [ARM64 Action43565277853](https://github.com/lly8666/wbd-next/actions/runs/43565277853) 已实际 SUCCESS，SOURCE `53b838a2d37d91ed5696e30c0ead9311e0615db5`，Ubuntu24.04 ARM64 本机 `uname -m=aarch64`；PLAN029 50/50（包括 FakeIP 两项多A小额度回收）、Game4 `r1_game_r4_g0` 13/13、FEC `r1_fec2_f2_` 12/12。纯组件/调度资格，不是 Linux ARM64 真实 TUN 网络。
- [H1807 Windows Action43565277807](https://github.com/lly8666/wbd-next/actions/runs/43565277807) **FAIL（未进入 Windows/WSL2 native）**：cheap `tests.test_m0_plan029_h1749_signed_direct_order::test_h1785_guest_cache_mode_is_explicit_wsl_argv_not_parent_env` 只识别历史 `"1" if p029_cache else "0"` 与 guest argv集合 0/1；H1807 给真实新多A scene 单独增添数字 2，已严格要求独立互斥，其余静态断言20项通过。修 H1785 对显式 0/1/2 的断言，并新加 H1807 A数、FakeIP隔离、真实两 OS Stop / SHA 断言；不把旧探针改为假通过，也不放宽实际网络证据。
- 此提交仅纠正测试声明，不重启已 PASS 的 ARM64，不重复 H1778/1799；同 SOURCE Windows 经原有工作流触发才执行真正 signed 场景。D3实网结果现在仍为 NOT_RUN，后续 D4/D5/P1/P2和 Game4 Split 仍 OPEN。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix only obsolete H1785 test-source assertion for newly explicit D3 guest mode 2; no product code, configuration, or behavioral change."}
```
