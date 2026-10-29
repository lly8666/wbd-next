# M0 PLAN026 H353 Rust Game native首错修复

SOURCE b606194a 的 Windows OriginalOwner Rust test (Action40820997024) 首错是 `native_game_due` 在非feature7的 Normal build仍引用仅 `fec2_product_record` 编译的 GameFec due 函数；给原函数恢复准确单份 `#[cfg(feature="fec2_product_record")]`，不扩大Rust产品功能或关闭Normal编译。Windows全库回归 (Action40820997039) 首错为新增测试 `std::mem::zeroed::<WbdWinGameNativeAttachV3>()` 初始化非空FFI原生函数指针，Rust明确拒绝，这是**单测自己制造的未定义初始化**：以严格NULL原生Attach/early/stats拒绝单测代替，没有改生产API或跳过别的测试。Linux Rust源原编译成功，Game网络与Stop真实验证仍NOT_RUN。

```feature-impact
{"kind":"none","ids":[],"reason":"只修复Game Native Rust非feature7条件编译和单测非法FFI初始化，无产品路径或参数变化。"}
```
