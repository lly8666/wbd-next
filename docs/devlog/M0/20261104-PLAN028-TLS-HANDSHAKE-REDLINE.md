# PLAN028｜用户建链外观红线与预共享route-key修订

日期：2026-11-04（Asia/Shanghai）。本次是用户明确授权的计划/提示词修订，不接管正在进行的产品编码或派发测试。

## 核验与决定

- 审阅main `c4f7910e4575ba4c00d2b1c7f424aedeb810fb59`，编辑基于更新后的 `2943b2754bf576b59ccecc3765dc28d7b0bbd4f1`，推送前接续到M0的新提交`516a23b8`/H1065，保留其切网工作、证据及在途结果。
- `v4_route_prelude.go:17–69`在ClientHello前发`WB-R1`+32B公钥，server先发、两向各37B；`admission_v4.go`空RouteKey分支调用它并只在该分支强制VerifyServer。原显式路径的HMAC SessionID可复用，必须同时解耦服务器身份验证，不能机械回退关闭验证。
- 用户允许显式预共享route-key并要求建链无私有协议特征。H1048前导方案因此明确废止；“只填账号密码”不再是阻止导入/填写key的要求。历史功能、认证和ARM原生PASS保留原范围，不构成外观PASS。
- 新唯一规范为`docs/architecture/TLS_HANDSHAKE_CONTRACT.md`。先做双方/平台调用及装配、配置/帮助、证书验证和定向握手审计；完成后续原PLAN028切网/交接任务。没有授权借机重写稳态协议、FEC/Game或启动全网测矩阵。

## 同步范围

更新章程/AGENTS/START_HERE、M0长期及028提示词、PLAN028、028–030总入口、029/030配置计划及对应提示词、registry M0目标、cursor下一步和现有认证功能卡。保留最新H1065 cursor原current_task、在途工作及最后测试SOURCE/evidence；不编造新产品结果。功能卡删除重复年表devlog链接以守16KiB上限，历史文件和逐SOURCE verification/evidence均不删除。

## 验证边界

本次仅文档/治理元数据，静态检查变更、JSON结构、引用与大小；产品源码/夹具未修改，未dispatch，产品修复与wire qualification **NOT_RUN / OPEN**。自动push治理检查结果以该提交Actions为准，不把本次文档完成写成代码修复完成。新握手验收必须区分标准TLS合法性、匹配基线的字段/长度、指定网站相似性；不以任意DPI绝对不可识别作为未经验证的承诺，也不得以此放宽零私有前导红线。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"User prioritizes standard TLS handshake appearance: reject H1048 pre-ClientHello exchange, allow preprovisioned route-key, preserve server identity verification; historical functional receipts remain scoped, product fix/wire qualification pending."}
```
