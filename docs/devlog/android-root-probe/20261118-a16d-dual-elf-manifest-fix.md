# A16d：双 ABI 原始产物清单真实校验修正

[A16c Action44230920834](https://github.com/lly8666/wbd-next/actions/runs/44230920834) 中 ARM64/x86_64 原 Rust 与原 Go Android Bionic 编译链接已走完，唯一 FAIL 是最后的 Python 产品清单：`wbd-v4-client-amd64` 尚未列入 ELF 元数据提取条件，导致对 `None["machine"]` 的 TypeError。此处**补上原 x86 Go ELF 的实际 machine62 和 PT_LOAD 校验**，绝不跳过原生机器码/源 SHA 验证；此前红门保留、D0 直到 Action 全门实际 PASS 才认定。D1/D2/D3、实体 ARM64 TLS/M4 仍 NOT_RUN；DNS 接管仍禁用。

```feature-impact
{"kind":"updated","ids":["android-root-native-client"],"reason":"A16 双原 Go/Rust Bionic ABI 已实际编译，修复最终 x86 Go ELF 元数据未被检查造成的 NoneType FAIL；新增真实 ELF62 校验，不降低 ARM64 原 ELF183/16KiB 红门。"}
```
