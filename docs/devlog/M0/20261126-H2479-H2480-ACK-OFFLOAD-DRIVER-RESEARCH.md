# H2479 验收 / H2480 发送卸载判别 / Windows 虚拟网卡选型研究（2026-11-26）

## 事实与修正
- H2478 run45780306808：4个9V45，D/F完整、E/H开启loan后连接重置且Stop失败，不能定位因果；不晋级。TX内核态占TX CPU约80–86%；WBD真实内层TCP反向segment多，不是外层ACK洪泛。D Copy source_wire_bytes 287528941、control_wire_bytes 726534、repair 893172。
- H2479 run45787098527，SOURCE 793c7e145，2/9匹配9V45，H/I 14/14真实交付完整。H/I稳态裸TCP MSS1049、250M，Windows全局+WSL vSwitch RSC ON/OFF/恢复：3.458/3.458/3.459%、3.455/3.460/3.452%。实际设置已改变和恢复；RSC累计合并统计查询JSON失败，不能排除其他聚合路径。MSS1460裸250两组5%；裸650 MSS1049两组1.695%。WBD250 49.988/50.671%，两组6000 ACK采样均正常推进（首个不可分类）、无SACK，实际237.34/225.97Mbps。WBD650 70.951/75.908%，H 6000 SACK且5999相等ACK，I 6000 SACK且5999推进；+25s累计重传111.6/126.0MB，实际243.98/317.53Mbps。全部严格clean_candidate false，非性能PASS。证据 docs/evidence/M0/H2479-ACK-RSC-ACCEPTANCE.json。
- 旧假设：Windows普通RSC开关决定裸TCP低ACK。上述同机A/B/A否定其简单形式，不再当作已知根因。新假设：裸TCP发送端GSO/TSO/netvsc或其他虚拟化聚合使ACK对应约30KiB@250、60KiB@650；WBD真实每2个MSS确认在健康低负载正常。该推论不是证明；Linux ss逻辑segment计数、接口skb和Windows NBL单位不等价。高负载缺口/乱序是第二独立机制，不能用减ACK掩盖。

## 公开实现核对与路线
- Wintun 0.14.1 https://github.com/WireGuard/wintun/blob/0.14.1/driver/wintun.c#L558 ：每个环包构造MDL/NBL，NdisMIndicateReceiveNetBufferLists(...,1,...)；同文件能力和OID未见RSC声明，逐包指示与真正RSC不同。GPLv2源码可fork，修改驱动需新签名并遵守分发许可。上游试验 https://git.zx2c4.com/wintun/commit/?h=sr%2Fgroup-ndis-indicates 研究最多16 NBL链式指示，非已发布RSC。Microsoft https://learn.microsoft.com/en-us/windows-hardware/drivers/network/overview-of-receive-segment-coalescing 。若证据支持，优先现有Wintun小增量：已就绪NBL批量（不等批）、再真正RSC元数据和合规连续数据合并，最后评估LSO/共享环；不从零重写，不假造大IP包或ACK。
- WireGuardNT https://git.zx2c4.com/wireguard-nt/about/ 是完整WireGuard内核UDP协议，配置API不是通用原始IP收发；不能替换后仍保留WBD wire/FEC/repair。可参考NDIS/owner实现，剥离协议并非低成本替代。
- sing-box 最新稳定v1.14.4依赖sing-tun 040db71fcd33，2026-11-26 testing依赖1a13df1ac21f；实际 https://github.com/SagerNet/sing-tun/blob/040db71fcd33/tun_windows.go 和 https://github.com/SagerNet/sing-tun/blob/1a13df1ac21f/tun_windows.go 均Wintun CreateAdapter/StartSession(0x800000)/ReceivePacket/AllocateSendPacket/SendPacket。新的用户态TCP栈不是新Windows虚拟网卡；引入会改变真实OS TCP及Rust稳态红线，不直接替换。
- Tailscale Linux TUN GRO/TSO https://tailscale.com/blog/throughput-improvements 可借鉴机制，不能直接移植Windows。WinDivert/WFP包级注入可做独立对照；WFP ALE连接重定向属于客户端TCP透明代理、不同语义，需另行授权。全自研NDIS或完整WBD内核面暂不施工。
- 决策：保留当前Wintun/NPF和WBD数据面，不做ACK过滤、等待凑批、恢复旧M2或新增防御措施。不扩大驱动签名/授权范围。当前优先定位ACK根源及650M前向损伤，之后用同机A/B验证TX小包成本。历史RX loan拒绝晋级。

## H2480 实验（启动时未验）
复用原9V45 CPU gate、同Windows/WSL2、原签名驱动、精确H2478 DLL及Linux构件、单TCP/400ms/0注入丢包/64MiB接收/MSS1049。原Windows RSC状态不改。裸250 TSO/GSO原始→OFF→恢复；裸650同样；WBD Copy250/650恢复原offload后对照。只改测试脚本/工作流；eth0 ethtool实际读回并恢复原特性，若不可改或原本均off明确跳过候选，不能记负结果。采集+10/+55s实际业务socket delta、+25s短时反向ACK推进字节直方图、随后前向TCP payload长度分布、抓包丢弃、offload活动读回、真实交付和Stop。Linux抓包钩子可能见分段前skb，不等同于线包或Windows NBL，样本窗口独立，不能用样本数直接算精确丢包。
- 判别：若OFF使大payload消失且裸ACK比例接近50%，恢复重现，则支持发送卸载路径机制；若大包消失ACK仍低，转查Windows接收合并/ACK压缩及TCP字节累计、pktmon/NDIS边界；若设置变了但大payload仍出现，干预未有效切断聚合，不能否定。若只高压下降速率，要区分供给变化、重传、ACK压缩；不把不同负载当因果。
- H2479 RSC统计JSON失败保留原样；H2480不是驱动开发，不开新产品分支。治理main游标仍停H2447，原分支治理Action已有失败，不虚称整体治理通过。本记录随PR78原实验分支保留，后续验收补具体run/结果。
