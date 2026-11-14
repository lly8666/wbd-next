# PLAN029 H1835｜源锁WinForms→真实Go --check-config选项读回，并在Game4早拒绝

- H1833 SOURCE `b433348` 原Windows/Linux编译已PASS：[Action43587003652](https://github.com/lly8666/wbd-next/actions/runs/43587003652) 精确manifest装配＋Windows Go产物/单测及Windows/Linux Rust单元回归success；[Action43587003694](https://github.com/lly8666/wbd-next/actions/runs/43587003694) DNS/CLI/Defender定向组件PASS。没有真实签名GUI起网场景，旧H1832装配失败保留。
- H1834在老`M0Plan028GUIButtonsVMHarness.cs`插入新分流控件、便携rules→fake Session的配置字节断言，但其变动未触发当前SOURCE H1663 WinForms工作流，故H1834 GUI测试仍NOT_RUN。避免误判为绿灯。
- **H1835**沿现有`tools/m0_plan029_gui_address_mtu_harness.cs`真WinForms＋当次Go CLI `--check-config`，在原有DNS单值/MTU1460/inner只读/旧DNS迁移负测同一GUI场景新增：真实字段`split-enable`默认off、`cn-rules-file`相对portable；在Normal选择后保存为owned小规则文件，`Effective`转换为Root内绝对路径，`ClientSession.ValidateAsync`实际Go返回`split-enable=true`与精确rules路径，保存重开保持意图；切Game4时显式CN split必须在CLI检查阶段早失败，不给「校验通过」再运行时报不支持，关闭split后原Game4纯Tunnel配置仍合法。
- Go原始`main_windows.go`没有由旧私CI gate控制新用户起网，H1835仅再加同一`--check-config`现有`*splitEnable&&*lanes!=1`早检查，Game2/4产品runtime仍双重fail-closed；重新计算这个manifest补丁的`result_blob`，没有触摸TLS/WFP/MTU/OS WAL。此批真GUI自动Action **NOT_RUN**，真实signed Npcap/Wintun、OS Apply/Stop与业务出口也**NOT_RUN**；GUI/mock/CLI校验通过不等于029 D5全部验收。
- H1831源268多A/CNAME真实DNS FakeIP/Direct UDP/Stop PASS_SCOPED独立保留；P2 Direct约22倍慢、P1 CPU未归因、慢fsync跨流HOL与Stop、Game4 CN后端、D4 IPv6及真实GUI起停仍OPEN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Reflect explicit early --check-config Game2/4 split refusal, matching existing cold runtime fail-closed, and source-current compiled WinForms→actual Go CLI portable CN rules readback fixture; not a new networking entitlement or signed-Ready claim."}
```
