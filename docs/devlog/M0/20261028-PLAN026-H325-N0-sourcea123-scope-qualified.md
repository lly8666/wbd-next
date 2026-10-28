# M0 PLAN026 H325｜N0 10Mbps/300ms/0%/240s真实范围PASS登记（2026-10-28）

Action <https://github.com/lly8666/wbd-next/actions/runs/40648269441> 精确 SOURCE `a1238c4d6964f60d88e65e2668314160fefe038f`：真Windows签名Npcap/Wintun Rust Normal/off ↔ Linux WSL2 raw/TUN，双向TC各300ms延迟、0%注入损、各10Mbps UDP发生器持续240秒。日志 `WL_N0_TRUE_KERNEL_MEASUREMENT PASS_SCOPED_300MS_0PCT_10MBPS_240S_BOTH_DIRECTIONS`，双方UDP/TCP和owned Stop PASS，TC owner清理完成。这是**单次、明确条件的PERFORMANCE_PASS**，不能把10Mbps说成250Mbps或物理产品资格。

独立250Mbps/200ms/30%首测 SOURCE `0d09cd5e` Action40651485360 因发送端仅148/108Mbps而 `CAPACITY_LIMITED`，真实两端Stop成功；优化发生器重测SOURCE `c8352931` Action40653341765 的终态需单独读取，禁止继承。新RX Stop优先级源码 `f753e612` 晚于SOURCEa123，不能用旧N0证明新代码的满载停止。

```feature-impact
{"kind":"updated","ids":["normal-off","windows-native-transport"],"reason":"将SOURCEa123真正核验的双向300ms、0%、10Mbps、240s N0限定为单场景PERFORMANCE_PASS；与SOURCE0d09的250Mbps容量受限及新版本待测保持分隔。"}
```
