# H2147｜Game2/4原生真实验收前修正旧廉价门

[Game2后置TCP双lane修复44a69d3](https://github.com/lly8666/wbd-next/commit/44a69d3a51dc6aab46fa89789b1e798c3c7180c6)源于原Action44221640214在原两条TLS/Wintun Apply PASS后被Go`len(members)==4`所拒绝。修复后Action44224645603仍未进入原生场景，首次FAIL是过期测试`if p029_game4_cn:`，新的通用Game场景用`if p029_game4_cn and not p029b_game_case:`避免重复配置。

仅更新相应静态断言、将新增双/四lane后置TCP检查添加到原有廉价测试、同步16KiB功能卡（“接线候选而非真实PASS”）。不改Rust FEC/wire、原真实B4与Game4历史回执。下一单Game2先进真实DNS、Direct/Tunnel TCP/UDP、Stop，未验/未完成保持NOT_RUN。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"Make exact source feature card and test selectors reflect shared Game2/4 Rust cold-split candidate, while preserving current-source native qualification as NOT_RUN."}
```
