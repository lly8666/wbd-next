# PLAN029 H2024｜保留H1581旧验证、不重复dispatch
- 原 H2023 [治理维护Action43894787607](https://github.com/lly8666/wbd-next/actions/runs/43894787607)仅旧PLAN028 H1581测试要求`WBD_WL_PUBLIC_MODES`行**第一个**分支必然是H1581。新唯一Game4 CN标记的显式优先分支放在行首，H1581同一代码行中原谓词/auto-AES256/mixed场景未移除；静态精确前缀断言过时。
- H2024改为校验该变量存在、旧H1581 marker仍选Normal及新增Game4独立marker选Game4；无产品/工作流/测试容量改动，不再触发Game4或padding场景；独立H2021/H2023在途收件。
```feature-impact
{"kind":"none","ids":[],"reason":"H2024 update only PLAN028 historic static workflow predicate test for preceding explicit Game4 CN selector; preserve H1581 and avoid new native dispatch."}
```
