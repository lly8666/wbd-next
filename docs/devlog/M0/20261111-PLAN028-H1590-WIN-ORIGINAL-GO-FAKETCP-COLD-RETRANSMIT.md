# PLAN028 M0 H1590｜修复 Windows 原始 Go FakeTCP 冷 TLS 缺失的真实重传泵

日期：2026-11-11；**PLAN028 IN_PROGRESS**。本项改真实产品原始Go Windows冷建链代码，区别于以前仅修测试夹具或Workflow。新 SOURCE **尚未经历Windows2025真实30%场**，因此本记录不宣称恢复已PASS。

## 真实问题、证据与最小根因

- H1588 SOURCE `5f0ac32ba0b5d933337ed88f0b33f54da579ac9c` Action `43002178705` 真 Windows2025 签名Npcap/WSL2 TCP443，0损非此场，**真实双向30% loss、单程200ms**，原始证书TLS/Go凭据尚未建立：`faketcp: bootstrap stream deadline exceeded`。Npcap `native-windows-npf.log` 捕获客户端原始 SYN2、服务端 SYNACK4、真实 ClientHello PSH一次、后续纯 ACK，**15s 冷阶段无 ClientHello数据重传**。服务端只有初始 M4 listener/TUN，未获得认证，内核反向 UDP helper只绑定没有发包是正确fail-closed。原始证据 `docs/evidence/M0/PLAN028-H1588-SOURCE5F0-WIN30-COLD-TLS-BOOTSTRAP-FAIL-20261111.json`，旧 Action 保留 FAIL。
- 源码 `r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go` 真实 `faketcp.ClientAssociation.EmitRetransmitDue` 仅在 **SYN waitHandshake** 期间由100ms ticker消费；`WaitEstablished` 成功离开循环后，原始阻塞 `V4WindowsEstablishOriginalClientOwner`/证书TLS/凭据请求/受保护应答期间再无人驱动该 Sender 的 RTO。丢 TLS 的实际PSH/数据后，尽管 `r0/go_overlay/internal/faketcp/client_association.go` 已有 `ClientAssociationEstablished` 的 `sender.RetransmitDue`，它无法触发。Linux多session server 原有主循环始终定期 `table.EmitRetransmitDue`，不是另一套仿真网络。**这是代码级事实，是否足以恢复30%需要新的真实Action验证。**
- H1583 SOURCE `e207fa95` 曾在某次同损VM真实完成TLS却因夹具没源UDP首反向失败；所以30%不是必然无法TLS，也不能由一次新试验代替稳定可靠性结论。

## H1590 最小产品修改与必守边界

只在 Windows **成功 SYN 后到 original Go TLS/credential/Rust Commit 结束** 启动一个有界、同 `ticker.C` 的冷阶段消费协程：100ms查询**同一个** `assoc.EmitRetransmitDue(time.Now())`，只在 `faketcp.ClientAssociationEstablished` 工作，复用原 `Sender.RetransmitDue` 的 immutable真实待确认数据/原 seq/ACK，没有第二套seq、Go伪ACK、伪造收包或Rust密文重做。异常的真实 Npcap 发包错误向外传并 `assoc.Close()` fail closed；若认证/Rust owner已开始，保持确切 scoped Stop，将Stop失败与根因一起返回。TLS结束后 `close(coldPumpStop)` + 等待 `coldPumpDone`，**Rust M3 native拥有数据面前已经joined**。追加只读 `WBD_WINDOWS_ORIGINAL_TLS_COLD_FAKETCP_RETRANSMIT copied=N joined_before_Rust_M3=1`，此数是原 Go TCP重传次数，不是内核成功到达或认证。
保留原两端 `TLS.Timeout=15*time.Second` 候选上限、当前认证、证书/route-key、MSS1420、原Rust AEAD+PN、原Signed Wintun OS CAS/WAL、物理路由/management owner/完全Stop。没有新增可在稳态轮询的Go热路径，没有超时放宽或凭据降级。

现有 Windows signed30%场使用**原** `[plan028-h1579-win30-cold-auth]` marker，另带 `[plan028-h1590-win30-cold-retransmit]` 只触发源契约。H1579真场必须在 `WBD_WINDOWS_CLIENT_READY` 前有真实原 Go冷期 RTO marker，并落地`h1590_original_windows_cold_tls_real_retransmits` 可审计数值，后续仍受实际Linux内核反向UDP、Windows Wintun OS手动/32读回、Linux Rust TUN reader_joined1、Windows WAL/WSL/netem Stop原严格门裁决。源级测试`tests/test_m0_plan028_h1590_windows_original_cold_retransmit.py`只是结构约束，**无法代替**原始30%产物。

## 预期实验判别（不预写答案）

新 Action 要先通过 Windows Go产品编译/Windows/Linux Rust，才可进入真网络。如果仍先在15s超时，必须看原 NPF `TCP443 flags`、真 `copied=N`、Linux server cold association拒绝/重传，进而区分原 sender RTO、server loss、客户端ACK或资源寿命。只有真实受保护TLS+Rust M4、实签Wintun OS、源/反向原生UDP和owner Stop全部达门，才给 **30%冷TLS PASS_SCOPED**，其余全 30%五客户端真实150s、30%吞吐600s/250–300Mbps、双Windows多实例竞争、1800s L3仍NOT_RUN。H1586 dd82的0loss150s真正PASS_SCOPED独立留证，旧 Action overall FAIL 不洗绿；不启动029/030。

```feature-impact
{"kind":"updated","ids":["windows-native-transport"],"reason":"H1590 changes the actual Windows original-Go protected cold TCP/TLS lifetime to keep the existing FakeTCP Sender/RTO active until credential authentication/Rust detach, then join before the original Rust data path; updates the Windows native transport feature entry without changing default TLS deadline or crypto."}
```
