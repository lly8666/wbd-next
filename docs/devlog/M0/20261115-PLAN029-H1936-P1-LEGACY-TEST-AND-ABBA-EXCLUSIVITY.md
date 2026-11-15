# PLAN029 H1936｜修复旧P1两段静态断言，保留其语义后才运行新ABBA

- H1935 [Action43731527099](https://github.com/lly8666/wbd-next/actions/runs/43731527099) 真正cheap测试`test_h1819_p1_source_frozen_moderate_normal_single_vm_two_legs` **FAIL**，因为旧的`("A_off_old_tunnel","0"),("B_on_all_tunnel","1")`恰好变化为显式三元组（第三项注明`legacy_tunnel/all`以兼容新的统一四臂循环），原有旧两阶段V4-vs-V3历史对照**仍然是相同的原始两binary和路由语义**。新测试逐一assert旧A和旧B及新四臂选择器，绝不删除旧单元测试，不伪装成原生网络问题。
- H1934、H1935 Windows/WSL2产品业务全部被廉价前置预检跳过，**没有源锁真四臂CPU证据**。这次同两个marker派发一个H1936原源签名P1测试；不启动长10GiB，避免重复编译同来源。
