# H1024｜PLAN028同账号两安装＋另一账号同端口真实并发、同安装接管不踢兄弟

## H1023精确原生实测结果，作为本次增量的不可偷换底座

H1023 SOURCE `96a420a0e2e5fd811272440be90700a5c35b6c34` `PLAN012-COMBINED-REAL-GO` Action `41592889627` native job `125773444318` **全job SUCCESS**。原Go保护TLS零server epoch 新相同InstallationID重叠端原生单测PASS；Linux四隔离netns实际旧Alice仍运行时，新Alice以同一安装凭据/TunnelID新五元组认证、服务端保留原逻辑epoch/32并起新Rust M1/M4，旧A精确Stop，独立账号Bob在切换期间继续UDP6；真实 `routed=46 unrouted=0 backpressure=0` 并原生Stop，原网卡/应用回显全部为真实Linux系统。源锁证据：[H1023](../evidence/M0/PLAN028-H1023-SOURCE96A-ZERO-EPOCH-NATIVE-SAME-INSTALL-HANDOVER-20261103.json)。1%真实netem测试512发/506收到/6缺失，没有改写为零损。Fixed/Auto仅短64包真实首交付，Game2/Game4限定Native PASS，Game+FEC最高待测。原Action `41592889681` Governance job成功但Feature Catalog **FAIL**：本H1023开发日志声明同时更新 `idle-rotation-keepalive` 功能卡，但原提交只更新 `tls-auth-multiclient`；非产品数据面FAIL，H1024补齐原卡及来源，保留原失败记录。

## H1024真多安装隔离覆盖，而不是第二个模拟框架

H1023真实4netns已经验证A同安装重建与不同账号Bob共存；用户要求更高一级：**Alice两个不同InstallationID/两不同隧道/32，同时Bob另一账户，三者在同一端口同一个Rust TUN内持续UDP**。这轮不再造场景框架、不加新稳态worker、不替换已有BPF/Original-Go TLS/Rust M1/M4。直接扩原 `tools/m0-plan028-two-client-real-linux-netns.sh` 的同一个源码编译二进制、同一个服务端PID、同一server443、同一真正Rust TUN reader：

1. Linux五个隔离netns：server、Alice原安装A、Bob安装B、Alice另一个安装D、Alice同安装接管候选R；桥接各自原underlay veth和自己的TUN。绝不重复创建服务器或第二个TUN reader。
2. A5包，再A+Bob各12包，接着起Alice另一个独立安装D，等待**第3条原TLS/Rust Ready、第三个真实自动/32不与前两个相等**，A/B/D三者同时各6包，证明同一账号两安装加另一账号同在且隔离。
3. 旧A进程仍活着时在第四客户端netns起候选R，用**与A相同安装文件**新五元组/新原TLS/新Rust incarnation，服务端原`same-lease-new-generation`精确Stop老A。R、Bob、Alice第二安装D同时各6真实UDP，Bob/D从未换generation，不能被A的接管干扰。
4. 对A/R/D分别原真实Rust Stop，Bob单独再5包，最终Bob/server Stop与Rust单reader join。原APP回显共 `5+12+12+6+6+6+6+6+6+5=70`，共享Rust读者路由计数应`>=70`、新源原始Go真实TLS会话4次、三个不同自动租约、服务端新旧交接Stop一次且最后老owner清理零残留。
5. 同一 `PLAN012-COMBINED-REAL-GO` Action在原步骤上加 **必须匹配**`M0_PLAN028_REAL_THREE_DEVICE_SAME_ACCOUNT_TWO_INSTALLATIONS_ANOTHER_ACCOUNT_ONE_PORT_NATIVE_PASS`；仍继续本源码同一编译之后的1%/FEC/Game原生场景，最终Mandatory gate严格fail-closed，绝不将C-BPF32纯单测替代app echo。
6. 更新 `tls-auth-multiclient`、`idle-rotation-keepalive` 原功能卡，前者新增H1023准确来源及H1024 pending，后者补齐H1023原native handover真实功能影响来源，避免H1023 governance目录声明不一致。保持前序证据与source字段，不删除真实失败。

**目前H1024 SOURCE提交前仅是`IMPLEMENTED_NOT_TESTED`。** 新同源码原生 Linux五netns真实场景没有Actions PASS前，不能将三设备资格写成完成。七模式A→A+B→B、Windows/Linux原生网络变化通知→出口重绑、200/500ms storm收敛、FEC Game4最高/MTU真实缩窄、CPU/p99与物理/Android均不在这项真实UDP资格内。H998物理MTU/ARM64 Game4FEC旧FAIL和Win/WSL2 Game4 lane2握手失败原样保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient","idle-rotation-keepalive"],"reason":"H1023 exact 46-real-UDP same-install Rust generation takeover verified and catalog card repaired; extend the SAME original Go protected TLS/Rust multi-netns native scene to three simultaneously leased devices across 2 accounts, 70 actual OS UDP echoes, with old-A replacement and unrelated siblings preserved. SOURCE native still pending."}
```
