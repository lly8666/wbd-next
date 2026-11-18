# H2183｜Linux随机启动填充编译FlowKey二次缺项与功能卡同步

H2181原生Action44266160914因模块 `v4_client_startup_padding` 根编译门不含Linux失败；H2182修复后 [Action44266740093](https://github.com/lly8666/wbd-next/actions/runs/44266740093) **原生x86_64/aarch64双作业Rust compile E0432失败**：portable `v4_client_startup_padding`依赖`v4_client_split::FlowKey`，根`v4_client_split`仍仅编译`windows/test`。H2182全量native-functional亦编译失败、feature gate提示`startup-flow-padding`本提交未修改feature卡。两轮网络**NOT_RUN**，不能当Linux填充PASS。

此批仅把纯Rust `v4_client_split`无IO的流键/分类模块cfg加Linux；在本次与padding同源的静态测试中核模块存在，增量更新填充功能卡的事实/首错而不提升network资格。Windows既有逻辑不变，Linux只在已认证Game2/4 group开启padding，Normal/Fixed/Auto非off仍明确拒绝。保留真实原Go/TLS/Rust/AF_PACKET pad字节及双向TCP/UDP/Stop/MTU硬门；新原生两ISA各8互补场必须先通过编译再实测，不能用旧H2177基础10/10或Window H2169代替。旧历史FAIL保留，PLAN029/029B完整OPEN。

```feature-impact
{"kind":"updated","ids":["startup-flow-padding"],"reason":"Repair pure FlowKey module Linux compile availability for existing cross-platform Game startup padding; synchronize failure/pending native verification in feature card; no qualification promotion."}
```
