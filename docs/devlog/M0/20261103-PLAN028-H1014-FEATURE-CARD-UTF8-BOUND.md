# H1014｜PLAN028功能卡原UTF-8大小限制修正

H1013首次缩短`game-lanes`功能卡，仍在当前GitHub Action 41579974283功能目录检查中失败：目录检查按文件`stat().st_size<=16384`核验**UTF-8字节**，而非JavaScript/Go的字符串字符数。旧卡15,857字符、实际16,823B，仍越限。H1014仅对原卡去冗长重复和紧缩JSON序列化，当前15,381 UTF-8字节，保留21条verification、对应SOURCE/证据、status，以及原历史FAIL/NOT_RUN范畴。产品代码未改变，不重派独立业务场景。

H1013 SOURCE74b1 Rust非FEC条件构建已在NORMAL-COMMON Action41579974321通过。真实`PLAN012`同SOURCE自动IP场景需等Action41579974216确认，不先写PASS。旧PLAN020 revision3静态审计与现revision4不匹配独立保留。

```feature-impact
{"kind":"updated","ids":["game-lanes"],"reason":"Fix exact feature catalog maximum UTF-8 byte size, preserving all existing 21 per-SOURCE verification rows and known failures; no product-qualification promotion."}
```
