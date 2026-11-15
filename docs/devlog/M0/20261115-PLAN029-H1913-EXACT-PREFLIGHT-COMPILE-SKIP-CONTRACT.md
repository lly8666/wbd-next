# PLAN029 H1913｜保留完整编译预检条件等值锁，允许已证明的H1909构件复用

- H1912 [Action43704549848](https://github.com/lly8666/wbd-next/actions/runs/43704549848) GitHub YAML已合法、Job已创建。Windows Go preflight、WinRust preflight、LinuxRust preflight及Linux source locked build四个昂贵编译job按H1911复用source marker正确SKIPPED；但**cheap tests.test_delivery_ci.test_preflight_has_no_native_runtime_or_driver_effects FAIL**，原静态fixture对完整Windows compile-only `if`有字面等值校验，不允许新增加的source-verified marker，签名网络因此没有跑。
- 本次**保留`self.assertEqual(job.get("if"),完整条件字符串)`**，只在旧完整预期式前追加`(!contains(... '[plan029-v3-real-p2-reuse-10gib]')) &&`，并且新增显式标记断言。绝不删除这个回归测试、宽泛地允许其它marker绕过编译，更不动SDK/Go/Rust产品、分片actor、数据面或OS Stop。
- 下个SOURCE应同时看到cheap PASS、治理PASS、四重编译SKIPPED、原Windows runner从H1909已签名Action43700145002下载实际EXE/DLL/Linux原二进制并验证run SUCCESS、二进制manifest SHA256、`git diff -- crates r0... Cargo.lock...`为空。只有最后的原生10GiB+96B UDP+双owned Stop整体SUCCESS才发布新CPU/GiB，不能将H1912/13的编译skip当产品通过。

```feature-impact
{"kind":"none","ids":[],"reason":"H1913 updates only exact static test string for the verified H1909 compile-skip condition, preserving strict equality and all driver isolation gates. No product change."}
```
