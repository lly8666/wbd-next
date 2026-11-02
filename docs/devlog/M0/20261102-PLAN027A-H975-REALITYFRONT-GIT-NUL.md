# PLAN027A H975｜Realityfront测试源锁NUL字节校正

H974新增的精确2文件测试源锁复制功能方向正确，但Python哈希表达式无意使用了文本`\\\\0`而非Git blob要求的真实`\\0`。H975只修这个字符，保持对所有其他原Go文件的拒绝覆盖、与plan020 manifest相同的原始/结果SHA、精确两条测试变更规则。不会重写MSS代码或吞吐测试。H974产生的原生构建结果继续单独归档，不当作新源PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"Correct Git blob NUL delimiter in strictly test-only Realityfront manifest source replacement helper; no production behavior change."}
```
