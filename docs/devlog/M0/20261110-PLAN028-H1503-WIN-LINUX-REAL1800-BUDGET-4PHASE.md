# PLAN028 H1503–H1505 | Win + Linux 真原生1800秒，低于宿主上限的多条件压力

恢复 main 12bf695623800fa9df962c9369ea0320779ec076，M0 H1502；用户要求 Win/Linux 同时1800s，强制不让虚拟机性能打满。先收回最新 Windows 600s Action42743477869：原始 ZIP13731432078 CRC和 SHA 8a5ac3f765e085c4c52799731e1f6e3081ad2ae85f94c4feba220e434ba64f22 PASS；新源码282a17d真实 signed Npcap1.88/Wintun0.14.1 Windows Alice + WSL2 Linux Bob独立帐号共用原 TLS443/Rust M4，600.23s，Win 5572/5572 Echo、Linux5595/5595 Echo、两向反包均完成，真TCP10轮、资源5、CAS53、Windows Stop Linux真实UDP+TCP继续、所有owner Stop和Npcap/WSL清理 PASS_SCOPED。旧 H1457 600仅~9.3pps，最新这次同样低速功能基线，不能冒充正式压测。独立干净Win750s/50心跳与Ubuntu异机GH元数据观察也原产物CRC成功。

Linux H1505 **一个独立 ubuntu-24.04-arm** 原生五帐号五模式六netns，冻结H1497 ARM source1211fd51完整ELF/ISA-L ZIP SHA528821894b8aa3101f47f97c87d0cee7b7e79276f6fb6cf8ec922da7f80a80bc逐文件确认，真实1800s物理netem同时分布0/1/5/15/30%丢包及0/15/50/100/125ms单程。内层256/1024B混包，每端基准速率7/7/6/6/5Mbps，共31Mbps/dir，依300s 0.55×、600s 0.70×、240s 0.95×、650s 0.70×持续四段（10s额外warmup），最大29.45Mbps/dir。源H1498已实测51Mbps基准峰66.3Mbps/dir，server 0.7826核/平均；新最大负荷理论约44%旧峰但不假定CPU线性。守护每10s /proc/stat逐核及MemAvailable，连续30s宿主总忙≥85%或任核≥97%或RAM可用<0.75GiB立即向夹具Python发SIGINT并由原finally cleanup，标CAPACITY_LIMITED，绝不报PASS。原10方向UDP/TCP、server真实认证B和Game整组、8-slot queue、实际netem/CPU、Stop六owner验收门完全保留。

Windows H1504 **另外一台独立 windows-2025 VM** 上做真实签名Npcap/Wintun与独立Linux WSL2客户端/原TLS443/Rust；只有托管VM内部 Linux namespace，**不是独立管理Windows DUT的最终1800资格**，仍诚实保留历史H1450同宿主Runner失联风险。不在GitHub管理NIC/WSL桥注入丢包以免打断Runner；600s原生通路构建复用同Go/Rust代码，新工作流只在明确新marker启动一个1800，原服务端/身份/Stop/管理/32与两套日志不改。App真DATA四段 450s128B约9pps、600s256B约18pps、300s1024B约25pps、450s512B约15pps，两个独立原客户端同时进行；每5s Win32真实host忙率/可用RAM、持续30s ≥85%或可用<0.75GiB阻断；每120s原Win私有内存/句柄/线程、Linux RSS/CPU；每5s实时echo/reverse <1500ms、每60s真实双方TCP共至少28、/32 CAS至少60、每段实际OS发包严格非零、真实6001包以上，最终 Windows 先Stop Linux继续 UDP/TCP、server原生Stop及 WAL/路由/NPF精确清理。另跑独立干净Windows1950s+Ubuntu异机控制面观察，不把其成功替代业务证据。完整Windows独立DUT1800仍NOT_QUALIFIED。

只新建 H1505 Linux Action 和触发一次 Windows H1504 已有完整原生工作流（独立VM并行），不重跑已有 H1498/1499 两次1800。前置 py_compile、workflow YAML和SOURCE核验证明未改变任何Go/Rust产品和外部线协议。每个Action返回后必须读原ZIP、原UDP阶段/CPU/Stop硬门；未触发、前置fail或容量守护主动停止不能算产品PASS。Windows之前的Runner失联原FAIL保留，Android/物理NOT_RUN，PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Only test-only native per-platform 1800 profiles, real original UDP/TCP proof and VM safety guard; freeze original Go/Rust and protocol, no user DATA duplication."}
```
