# PLAN029 H2014｜一次正常Tunnel-only 0..500B填充真正NPF/Stop验收
- H2008 SOURCE `791fa076f650833c07a3b9a49aca3e1c42b67f35` 的新增Rust单测首次因E0502编译FAIL，原H2009 SOURCE `2cbeb2a878262b5fcf55f38b34f1fc29b0c8efd3` Windows/Linux Rust全库组件PASS、治理PASS，但其commit只有 `[plan029-v3-real-startup-pad]`，工作流 `WBD_PLAN029_NATIVE_V3_TRIAL` 必须另含 `[plan029-v3-real-tunnel]` 才能进入原生Normal，因此native job原为SKIPPED。所有历史结果保留。
- H2014**不修改产品、测试算法、MTU/协议、CLI或GUI**，只以当前SOURCE同时标记 `[plan029-v3-real-tunnel] [plan029-v3-real-startup-pad]`，从原有共享工作流唯一 Normal Tunnel-only `--startup-padding flows` 场景签名测试验证原Win2025/WSL2真实TCP+UDP、原Rust M1 authenticated NPF实际复制>0 record/bytes、双owned Stop；绝不把原Rust单测可采>256B等同于真实NPF一定采到500B，不加额外数据包或压力测试。
- 与H2013同CDN Direct源是**独立Actions/独立VM/不同网络场景**，不复发本轮同类；结果以Action实际结论为准，尚**NOT_RUN**。
```feature-impact
{"kind":"none","ids":[],"reason":"H2014 trigger exactly one previously existing signed Normal Tunnel startup-padding flows real NPF/Stop scene for source already implementing 0..500B; no source feature change."}
```
