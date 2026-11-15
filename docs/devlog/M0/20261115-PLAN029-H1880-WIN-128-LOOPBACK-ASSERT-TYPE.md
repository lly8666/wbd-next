# PLAN029 H1880｜Windows 128空闲同WSA分片双活单测类型首错

- [H1879 Windows platform real-test Action43664732661](https://github.com/lly8666/wbd-next/actions/runs/43664732661) 真实进入`cargo test -p wbd-platform --lib`，在`windows_direct_tcp.rs:595,597`编译器 `E0277`：长度一的数组`[u8;1]`不可与引用数组`&[u8;1]`直接做`assert_eq`。**WinSock socket 测试体尚未执行**；H1878仅依赖编译、H1879首次正确触发的不同边界全部保留。
- H1880仅把断言改为`reply[0] == b'A'`和`reply[0] == b'B'`，保证仍严格验证两条独立真实Windows TCP连接各自有效收到唯一字节。没有修改socket枚举、共享event reset、半关闭、packet queue、原Rust TX生产线程，也没有重复派签名P2。
- 下一步只收自动触发的Windows2025`wbd-platform --lib`测试真实命名输出，不能将Windows release DLL/386 engine tests取代它。旧H1877单flow签名P2+StopPASS、真实性能2.787x仍OPEN；高并发Wintun、sameVM CPU/延迟A/B未测，PLAN029持续。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix only two Windows 128-socket shared-event unit assertions to compile and execute actual WinSock regression; no production feature logic changed."}
```
