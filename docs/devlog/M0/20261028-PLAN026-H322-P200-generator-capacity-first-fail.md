# M0 PLAN026 H322｜P200真实首轮容量边界和发生器热路径修复（2026-10-28）

SOURCE `0d09cd5e61266b716aa5ade9bbce55a63120f2f1`，Action40651485360 真实 Windows signed Npcap/Wintun ↔ Linux WSL2 raw/TUN，双方 `tc netem` 单程200ms、30%随机损、250Mbit/s上限、真业务60s。内核TC真实配置/读回、双方首次交付、双方owned Stop与TC清理均运行；**Action结论FAIL，理由是generator自身未达到最低225Mbps输入门槛，不是网络未连接或Rust Stop失败。**

- Windows发生器148.0198Mbps、Linux发生器108.1181Mbps；Windows收到75.6973Mbps、Linux收到103.5692Mbps，首次交付占对端实际发送的0.70016 / 0.69970，与30%注入随机损吻合。日志原样 `WL_P200_TRUE_KERNEL_MEASUREMENT CAPACITY_LIMITED_OFFERED_BELOW_90PCT_250MBPS`。
- Windows原Go exe **含Rust DLL+系统调用**总CPU42.1719秒（kernel34.3594s，user7.8125s），采样约76.344秒；峰值工作集41689088B，不能据此判Go热CPU或加密瓶颈。未重哈希测试artifact，见[源锁记录](../../evidence/M0/PLAN026-P200-source0d09-Windows-Linux-capacity-limited-20261028.json)。
- 首个明显发生器上限来自原Python循环 `for range(32)` 加每迭代 `time.sleep(.0008)`，为测试端主动加速：只在P200模式预建mutable UDP payload buffer，`pack_into` 改唯一seq，最多每轮128短批次；只在剩余credit不足时短睡，并记录**Windows/Linux各自发生器CPU秒数**。旧N0十兆发送逻辑原样保留。
- 用完全相同的P200 source tag再次运行时，若input仍低必须区分原Python发生器CPU、Windows/Wsl网络栈和Rust M2 owner；不要擅自调高产品阴影额度/线程数来掩盖host瓶颈。线程级CPU程序独立采样，不算语言级调用栈；单Entry锁仍待量化。

```feature-impact
{"kind":"none","ids":[],"reason":"只改变P200专用独立Python UDP测试发生器复用buffer/小批次及诊断输出，不改变Normal/off生产Rust DLL或Go产品行为；保留容量受限FAIL收据。"}
```
