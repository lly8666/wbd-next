# PLAN027A H957｜Game阶段网络与当前ARM64并行

H955真实Game10/10已PASS，H956功能卡改为合法枚举，故不重测。新增唯一Game4FEC3Mbps、250ms、内核5→30→5%共210s场景，原owned IFB/eth0 kernel阶段各自读回，否定缺阶段的假PASS。只改测试夹具，不改生产Go/Rust代码，Windows/WSL2严格SHA复用H952已编译程序。另在AArch64 Linux原生runner构建**该目标架构一次**，同一个Go/Rust程序连测9个真实netns MTU边界。均属Action确认前NOT_RUN；原生DF0/DF1与028–030不假报完成。

自动push旧主工作流使用已存在的`[plan026-coding]`源码测试专用skip标记避免重复构建；独立workflow_dispatch原生实测不受其影响。默认外层1460，显式最大1500。

```feature-impact
{"kind":"none","ids":[],"reason":"H957 modifies only native harness/scenario/workflow; existing Rust/Go product and feature qualifications unchanged."}
```
