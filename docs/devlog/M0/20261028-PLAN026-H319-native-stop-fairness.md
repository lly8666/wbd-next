# M0 PLAN026 H319｜持续收包时 Stop 优先（2026-10-28）

恢复cursor H318后确认：`e5752611` 真实两端功能7模式 PASS Action40647662195，N0 source `a1238c4d` 真实双方向300ms、0%注入损耗、10Mbps持续240秒 PASS Action40648269441。此两个源码早于本次Stop改造，不能外推新源码通过。

经源码检查，原 `rx_loop` 等待列表是 `[npcap,early,stop]`，真实Win32 WaitForMultipleObjects 在同时就绪时返回最低下标；持续高包速会使Stop等待。现在改为 `[stop,npcap,early]`，并在每轮RX、每个early密文、每个最多32帧NPF读前检查同一 `AtomicBool stopping`。TX的等待也改为Stop首位，在每个8帧读和每次最多4组源包前都检查退出。

新 Windows 原生单测使用**真实 WakeEvent / WaitForMultipleObjects**同时唤醒三个事件，确认Stop赢并保持manual-reset，不依赖mock制造的退出顺序。最大未检查窗口限定为单个阻塞外部驱动调用；这不能代替真实Driver满载Stop回归。

其余agent提出的TX/RX同一Entry锁、20ms timer和复制成本，仅按同机实际CPU/锁等待决定拆分；不为了重构增加另一个加密owner或Hot FFI。新压测会独立设置单程200ms/250Mbps/30%丢包并区分流量 offered、delivered、各层drops，不能将其称为已过。

```feature-impact
{"kind":"updated","ids":["normal-off","windows-native-transport"],"reason":"修正原生Rust Normal/off高收包速下Stop可被就绪Npcap事件饿死的调度；补Win32事件同时就绪单测和SOURCE验收限制。"}
```
