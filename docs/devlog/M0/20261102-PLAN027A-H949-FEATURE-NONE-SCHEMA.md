# PLAN027A H949｜source不变，修正feature-impact none结构

H948源 `adc63a8b8af209dbe589d072403b7bceae8e038b` 的Action `41452689560` governance角色门已PASS，feature-catalog却FAIL，错误为 `invalid feature-impact IDs`：H948 devlog的 `kind:none` 未附本项目schema必需的 `ids:[]`。此次只修该JSON元数据和记录实测FAIL，不改Go/Rust/manifest/夹具。H948 Action `41452689481` 已通过cheap source-locked assembly检查，真实编译仍沿它继续，无须为本批文档重构建。

```feature-impact
{"kind":"none","ids":[],"reason":"Only correct previous feature-impact schema and bounded cursor; unchanged native code and source-locked product manifests."}
```
