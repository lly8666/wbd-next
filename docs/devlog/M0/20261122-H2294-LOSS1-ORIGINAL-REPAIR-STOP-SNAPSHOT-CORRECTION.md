# PLAN029/P1 H2294：1% 原生机会修复不是零重发——Stop 证据纠正，2026-11-22

原 Source `cc8f7308630f60f7de71f5ef2587f1468c503345`、真实 [Action 45031628979](https://github.com/lly8666/wbd-next/actions/runs/45031628979) **9/9 SUCCESS**。真实 signed Windows2025 Npcap/Wintun GoTLS/Rust →独立ARM kernel relay（双向200ms/1%）→独立ARM原GoTLS/Rust/TUN，两组分别3条冷会话 `A(FEC OFF/repair OFF)→B(FEC OFF/repair ON)→A′(FEC OFF/repair OFF)`，每条25s 4 TCP bulk + 160小TCP，Windows/ARM Stop与真实 netem 双向 dropped counters正值。全程未启 FEC，不是 Outer 第二套TCP。

|组|A OFF Mbps|B ON Mbps|A′ OFF Mbps|B对A/A′均值|B真实 kernel accepted 冻结密文次数|
|---|---:|---:|---:|---:|---:|
|a|1.406|1.487|1.506|2.129%|**7**|
|b|1.543|1.450|1.480|-4.069%|**5**|

**重大计数修正**：当前 `tools/m0_h2293_true_product_fec_loss.py` 历史 SOURCE 只取 Stop前的 `WBD_WINDOWS_NATIVE_PACKET_TELEMETRY.frozen_ciphertext_retransmits` 定期快照的max；那一阶段它为0，故原客户端每腿 JSON 声称 0，但**同一段原 Go/Rust 进程 Stop 的两条底层真实行**如下：

- 组a B `WBD_WINDOWS_NATIVE_M2_OPPORTUNITY_STOP repair_polls=16312 candidate_first=91 repair_accepted=7 repair_abandoned=84 authenticated_reverse_reports=0 ... joined=true`；`WBD_WINDOWS_NATIVE_OUTER_REPAIR repair_packets=7 repair_accepted_wire_bytes=1569 r_to_f_ppm=87 joined=true`；`WBD_WINDOWS_NATIVE_OUTER_CURSOR unique_candidates=97 checked_once=145 burst_wait=0 fifo_left=0`。
- 组b B `repair_polls=16066 candidate_first=84 repair_accepted=5 repair_abandoned=79 expired_first=3 authenticated_reverse_reports=0`；`OUTER_REPAIR repair_packets=5 repair_accepted_wire_bytes=694 r_to_f_ppm=40`；`OUTER_CURSOR unique_candidates=95 checked_once=139 burst_wait=0 fifo_left=0`。所有A/A′真 Stop均0，说明有效策略归属确实只在B。

原始工件 [组a](https://github.com/lly8666/wbd-next/actions/runs/45031628979/artifacts/14758576124)、[组b](https://github.com/lly8666/wbd-next/actions/runs/45031628979/artifacts/14758810410) 的 `h2294-out/B_repair/original-win-client.log` 直接提供这些行。修复 `H2316` 后要求加入 **M2 Stop + outer repaired kernel Stop + outer cursor** 三条独立 readback，严格互查 accepted_packets 和 M2 accepted，给旧定期 snapshot 独立字段，防止原样的“真实重发7条却报0条”误判。H2316源码改动属于后继SOURCE，**不篡改旧 Action 所载 JSON 或过去结论**。

因两组 B 吞吐一组小升、一组下降，且 R/F只有87ppm/40ppm，**不能称机会补发修复了原TCP拥塞掉速**；修复不是“空无一物”但只是很小的、条件受限的补发。Stop 显示 `authenticated_reverse_reports=0`，其候选可从原外层 appearance ACK-gap hint 来，不是认证业务ACK或 receiver confirmed delivery。这既没有证实端到端 repair 成功，也没有证实在5%下可靠。P1 5% 使用自己的原始 SOURCE 和证据另判。
