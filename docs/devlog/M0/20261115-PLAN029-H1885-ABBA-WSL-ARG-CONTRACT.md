# PLAN029 H1885｜ABBA Windows→WSL 参数传播和旧 P2 静态验证首错

- H1884 [Action43669350889](https://github.com/lly8666/wbd-next/actions/runs/43669350889) 只在Cheap workflow `tests.test_m0_plan029_h1749_signed_direct_order.NativeDirectOrder.test_h1849_p2_identical_app_nagle_and_failed_scene_udp_progress` 报错：老测试要求`Popen([*args,role,first,second,"p2bulk" if BULK else "p2paced"])` 字面形式，新显式ABBA参数增加了第五个角色附加参数；Windows/WSL2源还未构建，更没有真Direct或Stop结果。这不是数据平面错误。
- 审计发现 `tools/m0_plan029_h1815_p2_real_mixed.py` 底部 `if __name__=="__main__"` 仍仅允许旧4/5参数；修为4/5/6。旧4/5参数完全兼容，但ABBA模式必须带明确第六argv `p2abba`；普通新式6参数明确 `p2ordinary`。原有`p2bulk/p2paced`工作负载一致性不放松；显式比较运行时ABBA与argv选择，不允许仅通过Windows环境变量“推断”WSL Linux已启用ABBA。
- 同步更新此前字面形状静态测试，增加新argv6验证，保留应用默认TCP_NODELAY/4MiB/no pace/失败时UDP progress/高分辨率时间戳断言。不改任何Rust生产TCP算法、背压/Stop、NT驱动或防火墙。新SOURCE仍需要Windows/Linux Rust编译和**同VM原Linux TCP五次真实字节/FIN＋原Windows四次Direct＋同场Tunnel UDP＋双owned Stop**验收。H1884原Action失败留历史，PLAN029 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"H1885 fix only true source-locked P2 ABBA WSL explicit argv and matching old static fixture contract; no product feature change."}
```
