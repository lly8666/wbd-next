# PLAN027 H427｜2s 稀疏 Quality 窗口安全截短

重新取回 69bbe53 Auto native双端失败、a48c258 main最新源码与治理：64 source 真实业务已交付，但固定1024 PN窗口迟迟不能CLOSE，当然不能把旧每record M2 Applied PASS冒认新Quality。H427核心允许Sender在连续2s且见真实首发后经所有驱动结果结清，将认证 CLOSE 的上界缩到真实 last PN。接收端仍保存START最大1024-PN位图，只有认证 id/lane/epoch/direction 且无已验更高PN才接受缩短CLOSE，修订 last_pn 后的下一START不重叠；缺少 CLOSE 保持 UNKNOWN。新增稀疏64PN及高PN拒绝负例。生产双端调用与Actions尚未验，原失败保留。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Allow source-backed 2s sparse quality window prefix closure without burning future PN; bounded source-level tests and owner integration pending."}
```
