# PLAN028 H1486｜纯离线纠正H1485外层报表错：x86 Game4物理换路UDP5/5已真交付

原本 [H1485 Action42633209462](https://github.com/lly8666/wbd-next/actions/runs/42633209462) 是一个真实的native x86/x86原始Go TLS443/Rust Game4 fixed6 A→A+B→B 物理源IPv4 10.25.0.2→10.25.0.3、MTU 1500→1280 的有界专项。它从 [旧Action42630288111](https://github.com/lly8666/wbd-next/actions/runs/42630288111) artifact13679959152 **复用完全相同SOURCE57b和3个ELF原SHA**，没有重新编译产品；唯一改变原 bash fixture stale server READY 条件，保留真实B认证、旧代Stop、MTU及UDP硬门。

原 [artifact13681532478](https://github.com/lly8666/wbd-next/actions/runs/42633209462/artifacts/13681532478) ZIP SHA256 `085714614d26e8e50dd6d07f5288ae69d68e41c0153ddd4164ed49a957c7ea32`，CRC PASS、6原文件完整。原 `h1485-original-native.log` 明确完整输出：第一代5个真UDP；物理route get为 `10.25.0.3`；新TUN MTU=**1178**；旧代Game native RX退役有界；新的**5个真正UDP echo 100–104全部收到**；第二代真正M4 authenticated peer ready + Ready；原Game4全组owned Stop/新组接管、FEC6/独立TUN和8个真实TLS ClientHello无私有前导全部结束PASS。

为什么Action外层仍红：在真正native bash场景已经返回0、产物齐备后，新增的GH workflow `grep V4_PUBLIC_GAME_SERVER_B_CLIENT_READY ... h1485-original-native.log` 无法匹配。**原native fixture自身** 在持有的 `TMP/server.log` 验证了该真实服务端B健康认证与Rust route提升，和双端旧代精确Stop才会进入换路后的UDP；成功路径只转抄client新代Ready与最终摘要到工作流日志，未转抄 server B 原始字符串。这里是单独的**后置报表假FAIL**，不是业务没跑，不能重刷seed或因此添加双发/计时器。

本轮加入`tools/m0_plan028_h1486_game4_x86_offline_receipt.py`，离线锁定原 ZIP SHA/CRC、原 fixture git blob SHA、原product manifest、原始日志、5个独立UDP回声、路由与MTU、8个真实TLS摘要，原生资格分类 **PASS_SCOPED_GENUINE_X86_GAME4_PHYSICAL_SWITCH_FIVE_UDP**；原Action仍保留红态，详细区分 `FAIL_OUTER_POSTCHECK` 和 `PASS_NATIVE_SCOPED`。同一workflow改为只允许手动重新执行并移除不可达日志grep，**不自动再做网络**。

总状态：H1484 ARM64五客户端180s十个UDP方向0缺且Normal B6次/Game B2次实际证明 **PASS_SCOPED**；本次x86 Game4路径真UDP5/5 **PASS_SCOPED**；已有H1200独立短测及75Mbps容量/1800原缺失仍OPEN，Windows/物理Android未跑仍列。PLAN028 **IN_PROGRESS**。

```feature-impact
{"kind":"none","ids":[],"reason":"Offline original ZIP reconciliation and postcheck-only fix. No new data plane, native build, traffic generation or wire changes."}
```
