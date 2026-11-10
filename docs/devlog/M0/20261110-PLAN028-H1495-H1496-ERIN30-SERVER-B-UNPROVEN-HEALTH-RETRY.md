# PLAN028 H1495–H1496｜30分钟原物证到手：容量50→75真PASS，健康低损L3真业务合格，Erin30% B认证不对称真实FAIL

恢复main `8ba7d46efa617ddc083bd6ff038da1f6dae3a090`、M0 H1494；三条并行Actions全部完成，先取原ZIP并逐份SHA256+CRC PASS，再按冻结原client/server/Rust SOURCE57b日志和十个真实UDP方向核验，而不是 Actions 绿红代判产品。

**H1491 [Action42660921771](https://github.com/lly8666/wbd-next/actions/runs/42660921771)** artifact13695371981 SHA `b6f47708245416255edd92239d964956b057171edde64d101675f827a791f431`，同ARM64 VM顺序原生50→75两个180s：真实Alice 30/50/75/50Mbps精确送达74.999峰值，五人双向十方向UDP**零永久缺失**、共享TUN queue overflow0、六owned Stop都完结；50/75宿主平均busy47.96%/46.51%、最忙核48.3%/46.77%、server约0.47核。限定`PASS_SCOPED`。旧h1286报`ROTATION_CONTINUITY_NOT_PROVEN`系计划明确冷轮换3600s、180s容量无轮换，**不是应验但没触发的L3**，旧报表仍保留。

**H1493 [Action42660921629](https://github.com/lly8666/wbd-next/actions/runs/42660921629)** artifact13697290581 SHA `0ab86404895523f58f6c9f09690eac7c477460176c44f1683ac7768dd4408477`，原生真实1800s 0/0/1/1/5%损伤；原客户端Alice/Bob/Dave/Erin十方向中各自双向永久缺失零，Carol 1%物理损伤上行缺153、下行缺182；Game2/4实际轮换/全Stop PASS、服务端Normal B原生认证Health **69/69** 真接管、拒绝0、共享TUN overflow0。旧H1274仅把`V4_PUBLIC_MIXED_NORMAL_READY`当server M4，漏看新增`V4_PUBLIC_MIXED_NORMAL_B_CLIENT_READY source=authenticated_client_native_Health`，导致外层Action FAIL；原FAIL不改写，经原ZIP离线验证可判`PASS_SCOPED`，**只在原SOURCE57b下**。

**H1492 [Action42660921499](https://github.com/lly8666/wbd-next/actions/runs/42660921499)** artifact13697040991 SHA `8f4a91e701d08647cd85bab3975c40176d7a4ec5fba295d8588c5c679a712437`，真原生1800s 0/1/5/15/30%，Alice/Bob 0永久缺失；Carol Game2 underlay5%残损上/下缺6931/7012，Dave Game4零，Erin Normal Fixed6 30%重损**上/下缺907435/839580**，最长活跃发送无交付72740/128940ms，恢复段仅65.1%/70.6%交付。绝非报告器假红：客户端Erin21次READY，服务端B**12次独立`V4_PUBLIC_MIXED_NORMAL_B_UNPROVEN`**（五秒等待超时）、9次其余成功/重起始认证，server共享队列溢出0，最终Stop PASS。与0%用户和低损源反例对应，原native问题保留**FAIL**。旧报告的Normal server M4漏判需要独立纠偏但不能顺便豁免Erin。

源码直接确证：原`v4_native_health::HealthClock`服务器冷M4已有三次AEAD kind0 400ms间隔送证，但客户端新B`arm_client_cold_ready()`**仅一次**；底层30%单程丢包易丢失这唯一证明，客户端收到服务端cold M4就提升，而服务端没收到客户端Health保持A。最小修复仅将客户端M4**既有kind0**冷成功发送预算1→5（首发+4次400ms，1.6s内、每次AEAD fresh PN），原server3/steady15s/90s dead/单TUN路由/原加密数据完全不动；失败发送仍走原有>=1s冷重试，非稳态心跳/不跨代业务双发。新增L0断言恰五次、不忙循环、无新业务活跃、恢复15s稳态。H1496仅一真实x86五客户端180s 30% Erin边界，复用老Go ELF并编译新Rust ISA-L；必须实际触发Server B Health证明、旧exact Stop、零损Alice零唯一缺失才通过，不用直接重复30分钟。

配套H1495独立离线rejudge读取三原ZIP SHA/CRC，按跨Normal用户**端口唯一性**匹配原客户端生成的native READY与服务端initial M4或真实加密Health-B接管；保留原B_UNPROVEN和旧Action FAIL。H1495/H1496提交时均NOT_RUN待Actions；若后者FAIL不刷种子，精准保留首个真实失败。新修复SOURCE改变后，原H1493 L3资格不可直接当新SOURCE最终长测。Windows原生Npcap/Wintun独立设备1800未跑合格、Android/物理NOT_RUN、H998旧FAIL照实留存。PLAN028 `IN_PROGRESS`。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix existing authenticated cold Health proof reliability without wire/feature change; use original native ZIP offline evidence and one new bounded targeted x86 regression only."}
```
