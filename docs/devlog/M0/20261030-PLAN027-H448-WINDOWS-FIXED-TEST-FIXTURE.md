# PLAN027 H448｜Windows Fixed新认证窗口测试样本遗漏修复

H446 [Windows owner Action40988092490](https://github.com/lly8666/wbd-next/actions/runs/40988092490)、[Windows+Linux preflight40988092605](https://github.com/lly8666/wbd-next/actions/runs/40988092605) 产品源码可编译，但相同唯一单测 `plan027_windows_owner_authenticated_quality_close_matures_without_receipt` 行2750失败：`(first_sent,received_unique)=(4,0)` 预期 `(4,2)`。H446将认证 START 提前后仍留数据inject在只迭代CLOSE的分支，根本不发Unique DATA。H448精确把两个不同PN(100,102)写入已启动的RxWindow后再发认证CLOSE，保持原严格4总、2 unique、3s mature和 Stop 检查，不跳过测试，不将假数据喂入生产码。新 CI 待验，PLAN027 B/C 未闭环。

```feature-impact
{"kind":"none","ids":[],"reason":"Fix test fixture only for H446 Fixed startup signal, preserving runtime security bounds."}
```
