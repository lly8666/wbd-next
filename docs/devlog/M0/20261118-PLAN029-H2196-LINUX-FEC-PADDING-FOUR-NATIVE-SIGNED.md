# H2196｜H2195双ISA Linux FEC source tail padding原生签名

真实产品与夹具SOURCE `8a404a4f79227fde41286056f0c62c4d406f210a`，[Action44292569034](https://github.com/lly8666/wbd-next/actions/runs/44292569034) 两个独立原生Linux x86_64/ARM64 jobs **completed SUCCESS**，各自Fixed tls、Auto flows共四场原 Go TLS、Rust M4原始内核TCP/UDP双向、有效FEC kind2 source加密尾部填充、owned Stop和netns清理 **4/4 PASS_SCOPED**。内核AF_PACKET真正copied后：x86 Fixed tls每端2条417B、Auto flows4条1372B；ARM每端2条85B、Auto flows4条713B。外层1460B内层1375B，owned TUN IPv6已禁用；原文 source index/revision、parity kind3、repair不改。原x86 ZIP14422137104 sha481b1c0f、ARM ZIP14421308109 sha81ac2dea，各36成员CRC PASS，原三binary完整 SHA及两端场景明细见[签名 evidence](../evidence/M0/PLAN029-H2195-LINUX-FEC-SOURCE-PADDING-X86-ARM64-FOUR-NATIVE-PASS-20261118.json)。

历史治理失败保留：[44292569134](https://github.com/lly8666/wbd-next/actions/runs/44292569134) Linux功能卡原16499 UTF8字节超16384、[44293349881](https://github.com/lly8666/wbd-next/actions/runs/44293349881) doc-only提交声明四张卡但仅更改一张卡；本次四卡均同步原SOURCE/证据，待本次治理CI再宣布PASS。以前H2186 16场、H2193 Normal4场不是本SOURCE的全矩阵回归；无实际FEC高丢恢复/负载因果CPU、physical ARM、动态auto-IP物理MTU或完整应用TLS资格，全部OPEN/NOT_RUN。030未启动。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding","linux-raw-tun","fec-fixed","fec-auto"],"reason":"H2196 original native Linux x86_64/aarch64 authentic FEC Fixed tls and Auto flows kind2 padded-source M4 kernel copies, two-way TCP/UDP and owned Stop 4/4 PASS_SCOPED; preserve previous signed/source failures"}
```
