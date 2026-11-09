# PLAN028 H1478｜SOURCE66fb低负载换代第一丢失边界，先外部只读包头分辨

承接 H1477，`main` `3fe5e412f8b1`、cursor1477 无新在途Actions；原[H1473 Action42595013191](https://github.com/lly8666/wbd-next/actions/runs/42595013191) x86同VM五客户端rotating12 Alice DL13、Carol DL3，static12零丢，server shared TUN队列/retired均零。旧代随机10–20s仅RX grace，Game logical PacketID复制去重非跨代业务双发；没有依据更改正常唯一TX路由。当前确认L0/L1仅局部、028仍IN_PROGRESS。

**最小实验**：不改产品任何Go/Rust TLS/M4/record/MTU/Stop语义，复用原SOURCE `66fb6b4454b1ce4297ab04efa20c7f931ff12383` 的 H1461 x86原生双端manifest/hash（原构建Action42578056120）。新的单场[H1478 workflow](../../..//.github/workflows/m0-plan028-h1478-native-header-first-loss.yml)在同一VM运行原五客户端真实180s `rotating12`，只监控 server→Alice veth TCP-shaped 443外层 DATA。两段应用时间28–60s、119–151s，覆盖原39.39/132.85s丢失起点并两端各留1s匹配边缘。BPF只收TCP src=443、srcIP10.25.0.1、dstIP10.25.0.2；snaplen64、临时pcap最后删除；报文内容/密钥不入artifact，结果只含每port发送/物理收见计数、hash化少量头摘要、单调时钟10ms原业务缺失、观察者内核丢包和真实全owner Stop。观察到服务端物理egr不等于socket接纳，客户端物理ingr不等于Rust RAW recv/AEAD/TUN；这是区分假说的第一层，不冒认完整逐包因果。

**容量/扰动依据**：Alice单方向12Mbps、包型256/1024混合。按均值1024B保守估算约1465包/s，32s窗口约4.7万包，64B snaplen+pcap framing每接口约3.8MB；两个窗口每侧约7.6MB临时，结束删除；相比12Mbps线速，对产品无逐包热路径插桩。实际PPS、观察者掉包与CPU按真实产物判，若观察者丢包则不得由未匹配推断网络掉包；如换代业务缺失未触发，标NOT_REPRODUCED，原FAIL不作PASS。一个Action只跑rotating12，既有static12原PASS复用，不重复刷同场seed。本轮属于原SOURCE x86故障定向复现，下一独立Linux全任务优先原生ARM64交替。

结果到达前**没有候选修复**。等真实Action完成先核manifest、真实5客户端、产品Stop、pcap observer内核drop，逐代比较外层匹配与原500ms Rust M4、10ms应用缺失，再选择只读RAW socket/AEAD/TUN阶段或最小因果修复。不加跨代双发、稳态头、Go热泵，不扩队列/重发，L3不早验。原600/1800/Windows/ARM/MTU/Android范围及原FAIL原样保存。

```feature-impact
{"kind":"none","ids":[],"reason":"Only source-locked external Linux native diagnostic, no product or configuration behavior change."}
```
