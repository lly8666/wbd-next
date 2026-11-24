# Emulator fingerprint real SDK property guard correction

上一个故障工件 `14266715373` 内的 `ksu/build-fingerprint-second.txt` **实际为** `google/sdk_gphone64_x86_64/emu64xa:16/BE2A.250530.026.D1/13818094:user/release-keys`，并非 `generic` 前缀。因此让模拟器可见的用户触发示例按钮只匹配 `generic` 不足。仍保持强制 `Build.HARDWARE=ranchu`，但指纹可为Google Play实际 `sdk_gphone` 或AOSP `generic`。不在实体手机暴露模拟器 UI；此独立修复在新SOURCE测试前完成。

```feature-impact
{"kind":"none","ids":[],"reason":"Match actual Google Play Android16 emulator fingerprint sdk_gphone for emulator-only onscreen UID demonstration; preserve hardware ranchu guard."}
```
