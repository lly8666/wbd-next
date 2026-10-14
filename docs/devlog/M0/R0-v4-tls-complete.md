# R0-CONTRACT-001：V4生产非测试Go入口与真实TLS验证

2026-10-14 UTC。开始前按main registry与M0 cursor sequence6恢复，checkpoint ec10631c32fcb3e806e481aabeded40aca97f47c 到HEAD e4436826dedcd748e65ee18eaedc7ca59f026495 仅一个cursor H；当时无未完成Action，CLEAN不代表产品PASS。

**why_now**：从先前`r0/legacy_v3_v4_probe_test.go`的测试-only静态V4拼接继续到真实受TLS保护的双方读写，并验证epoch与错误门；防止把旧Go字节和Python代数误当已集成产品。

**实现**：非测试Go文件 `r0/go_overlay/internal/realityfront/admission_v4.go` 和相邻测试，在Actions固定旧 Go SHA `a7a82db31fe736ffedee330795a3234d358f1984` checkout后叠加编译。旧Go原始V2/V3 admission、uTLS/TLS握手和FakeTCP transition源码未修改，V4由显式`EstablishClientV4/EstablishServerV4`接入同一真实TLS流，单轮保护的req/reply，规范24B带features/epoch绑定。使用V4 exporter canonical reply与三cipher分向HKDF。server在认证与业务验证后才暂存epoch，Detach成功才commit；pending失败回退；store最大4096条可配置，ReleaseLane显式。无Rust capability时生产默认不进入V4（必须DataPlaneReady true，但这个布尔只能是调用者声明，不是自动的Rust资格证明）。

**Actions真实证据**：SOURCE `6aaba145289ea7771469ee5e462cce03361a432f`， [run38510931409](https://github.com/lly8666/wbd-next/actions/runs/38510931409) attempt1 completed/success。build job115679018829编译一次Go1.23.12；consume job115679162138验两端SOURCE、源码输入hash、二进制size/hash后执行。五组顶层测试全PASS，0失败：三cipher实际双方TLS派生、2lane共享/重复拒绝、错epoch/身份拒绝、能力/容量门、旧Go V3 TLS拒绝V4。build artifact11869084710 ZIP SHA256 4f270279cecb85464ffd65ed1055413f451655626f504071aba7f0b5de149c11，result artifact11869970326 ZIP SHA256 d515a5c5111f7e10dadee38964fe84758098385ff16a6427f83073e424cf10b5。独立[Governance38510931562](https://github.com/lly8666/wbd-next/actions/runs/38510931562) success，但不是产品测试。

**边界**：原应用的真实调用点和配置/CLI/GUI尚未接V4，Rust receipt/Game尚未实现、不能主动广播V4 feature；显式ReleaseLane未接产品生命周期；同一TLS请求重复回复缓存、跨client租约/rotation、ABI与平台探针还未测。R0总体仅partial，M1–M4仍reserved，旧功能/80s问题未移植/关闭，不部署。

**子任务done_when**：真正旧Go TLS双方5项锚点PASS并完整记录，达到本原子范围即停。

**唯一next_action**：在原控制程序调用点接显式V4 readiness/effective config门与epoch存储/退出释放，保证默认V3兼容与V4无能力绝不启用；以Actions精确验证，再推进Go↔C/平台ABI探针。
