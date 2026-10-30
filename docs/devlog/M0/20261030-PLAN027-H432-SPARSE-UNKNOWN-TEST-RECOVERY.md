# PLAN027 H432｜源锁H430纯回归96/97失败反例判定修复

在原 b4cc8e8 Action40977930885 recovery组实跑96/97，唯一失败 r2_plan027_truncated_close_refuses_higher_verified_data：收端没有接受认证 CLOSE，`mature_wire_report`先校验缺失的发送端F，因此结果本来就是 `QualityError::Unknown`，测试错误期待 `NotMature`；若把实现改成NotMature可能掩盖无F，违反未知不可变零损。本批只更正负例断言，严格保留source b4cc8历史FAIL。H431 Windows NPF索引Action仍在途，不能提前归零失败；A/B/C和Fixed/off线上M2退役仍开放。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Fix sparse authenticated CLOSE negative unit-test oracle to require Unknown when F was never bound, preserving safety semantics."}
```
