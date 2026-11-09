# PLAN028 H1475｜换代不是双倍业务，原始10ms持久缺包紧贴新代M4首采样

从已经完结的[H1473 Action42595013191](https://github.com/lly8666/wbd-next/actions/runs/42595013191) 原始75文件CRC_PASS ZIP（[artifact13663646307](https://github.com/lly8666/wbd-next/actions/runs/42595013191/artifacts/13663646307)）重核相同SOURCE `66fb6b4454b1ce4297ab04efa20c7f931ff12383` 原Go TLS/Rust M4五个认证客户端，在同一台Runner先rotating12后static12两个真实180s，原始六个Stop都有。

换代时实际Go `path_supervisor_linux.go` 允许1个current+1个candidate+1个old retiring，**Rust单共享TUN读取器**在新代实证M4之后仅将默认新业务派给新代；旧代保留10–20秒authenticated RX处理旧在途包。因此是“两套代际资源短时共存”，不是业务字节数必然翻倍。原Alice Rust M2第一份密文首发累计：换代3代合计294216166字节，不换代294143551字节，差72615字节即约+0.024687%；所有这些M2报告`repair_accepted_wire_bytes=0`与`original_frozen_retransmitted=0`。仅是**累计**，不能断言重叠半秒没有瞬时尖峰。

更强、无需再耗180s原生运行的结果：原始`h1250-s-alice.json`与`h1250-c-alice.json`使用完全相同Linux单调时钟起点，拥有19001个每10ms业务TX/RX唯一包桶。对其累计TX减累计RX求所有未来窗口的最小值（suffix minimum），将迟到但最终到达的包从**持久缺失**中排除；换代场Alice的13个最终缺失在39.39s(+5)、39.40s(+3)、132.85s(+4)、132.86s(+1)出现，不换代场所有用户全部0缺。原client Alice对新2代、3代的第一次`V4_PUBLIC_M4_EXTERNAL_STAGE_DIAG` 500ms采样mono_ns分别相对应用起点39.90s、133.37s，即两次缺包起点各比新代首次采样早约0.51、0.52秒。时间耦合很紧，符合handoff瞬间损失；但500ms采样不是精确promotion时刻，10ms桶也不是逐包抓包，不声称已找到第一丢失代码行。

原server Alice TUN offered=331225、client Rust M3真实`tun_delivered`合计331210，15差；server队列overflow0、两套Linux原生socket原始停止成功。M3含TCP/UDP不能把差15直接等同应用独立UDP缺13；必须继续按各代RAW socket RX、Rust M3和Go/内核TUN边界检测，不能贸然将retirement grace延长或写成业务双发补丁。H1467正序static0/rotating25、H1473反序rotating16/static0说明跟换代相关而非单纯“第二场宿主老化”，但仍非直接丢包栈证明。

H1475本次只新增一个廉价**原始产物离线重放**和单元守卫：检查原Go/Rust产品SHA、每场六Stop、原始19001桶、suffix最低计数及M4首500ms记录、M2首次实际TX累计。新脚本与原生产品SOURCE分开，绝无新网络/产品build或旧长测重复；直到H1475 offline Action真正结束结果标记NOT_RUN。Windows正式L3 1800仍NOT_QUALIFIED，SOURCE66fb原真实600高压32/45及1800混合零损Alice351仍FAIL_SCOPED，H998历史HOT FAIL、Android物理NOT_RUN、PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Original source66fb five-client 180s artifact-only 10ms persistent-loss vs per-generation 500ms native M4 stage exact accounting; no production, protocol, crypto or network workload."}
```
