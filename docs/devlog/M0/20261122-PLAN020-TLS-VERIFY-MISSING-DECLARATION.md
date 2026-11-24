# PLAN020 Windows 原Go产品编译修复：H2214 TLS 验证开关（2026-11-22）

旧真实 [Action 45032506062](https://github.com/lly8666/wbd-next/actions/runs/45032506062) `original-go-native-wal` 第一个错误为 `cmd/wbd-client/main_windows.go:392:94: undefined: tlsVerifyServer`，因此后继真实 Windows OS WAL 三机/GUI Job skipped，**不得叫 PASS**。原冻结 Go donor `a7a82db31fe736ffedee330795a3234d358f1984` 的 `main_windows.go` 未声明该 flag，而 `r0/go_overlay/assembly/manifest-plan020-m0.json` 已将 `TLSVerifyServer:*tlsVerifyServer` 绑定进受保护的原 Go TLS 配置：源锁 patch 遗漏导致编译不成立。

本次保持 source-locked donor 与原 pin SHA 不变，在 **同一 manifest 原 Go CLI 受控补丁**中显式增加 `tlsVerifyServer = flag.Bool("tls-verify-server", false, ...)`，默认严格遵从用户此前已接受的 H2214 **OFF**，仅主动选真才执行证书校验；**不擅自改默认 ON**，不碰 Go TLS 密钥交换、Rust 数据面、Win WFP/WAL、其他默认。程序集 SHA 从原 `28a46730b5455bf18bbcbb61e1cdadf2691b1663` 计算更新到 `3238f8819563c51bc34c33f5e884f9d36c421231`，由 GitHub Git blob API 对原 Donor + 全部受控补丁的实际 bytes 计算，比对旧原结果 blob 已核验过一致后才追加新补丁。真实 Win2022 编译前同时校验 flag 唯一和 `TLSVerifyServer:*tlsVerifyServer` 唯一；主线预检及源锁实际 CLI build 不得跳过。原 H2214 [QA](https://github.com/lly8666/wbd-next/actions/runs/44470462032) 是另一条来源的旧 scoped pass，不冒充本次最终 Windows5-stage OS WAL PASS。

```feature-impact
{"kind":"none","ids":[],"reason":"仅修复已登记并已有H2214设计/QA的Windows CLI TLS验证默认OFF旗标在PLAN020固定Go程序集中的漏声明；无新用户能力、协议或默认档变更，最终本SOURCE产品资格仍取决于完整原生Action回执。"}
```
