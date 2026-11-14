# PLAN029 H1855｜修正冷Npcap路径的真正 native 自动入口与同SOURCE cursor

- H1852 Action43610536189只在`prepare_windows_wiring.py --check-only`遇装配blob mismatch，真实Windows编译/签名Wintun/P2未运行；H1854 source c84cf40 已更新两个精确result_blob，不取消manifest、不破坏pinned donor。
- 旧native工作流`push.paths`不含`r0/go_overlay/assembly/manifest.json`及两个`internal/faketcp/npcap_native_handoff_windows*.go`，故H1854新SOURCE没有在途真实网络。此次只追加3个精确路径触发，保持`[plan029-v3-real-p2-rebuild]`既有场景条件且不恢复旧28矩阵。
- 从H1853原生governance Action artifact `structure.json`见`BLOCKED: evidence is for a different SOURCE`：cursor.last_tested_source仍是H1851 `998d3df3`，却混入H1848/H1850等不同source证据。H1855使当前evidence_refs只含新增H1852负面汇总（`source_sha=998d3df3`），其他历史证据原文件保留，非删除结果；治理校验准则不改。
- 本提交触发**一个**新SOURCE签名Normal P2，观测原Go reader join后`pcap_setnonblock=1`与`pcap_getnonblock=1`是否真正可用。冷初始化失败、TCP仍慢或完整成功分别按实测标记；提交时NOT_RUN。仍需全部029验收出口。

```feature-impact
{"kind":"none","ids":[],"reason":"Preserve source-specific evidence and exact 3 native workflow source triggers for Npcap handoff and assembly; no product behavior, performance qualification or old 028 scenario change."}
```
