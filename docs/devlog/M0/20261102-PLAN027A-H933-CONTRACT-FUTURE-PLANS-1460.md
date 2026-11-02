# PLAN027A H933｜MTU 唯一规范与028–030默认同步

紧随真实产品 SOURCE `f2a6644908ecf567bed17987e51099e5cbd0d7da` H932 原Go/LINUX V4/GUI/参数目录1460默认更改，现修 `docs/architecture/MTU_CONTRACT.md` v2、PLAN027A与028/029/030及对应提示词，防下游误沿历史1500默认。**默认1460≠最大1500**；手动配置1500依旧可用，1500 GameFEC1398 golden与1500:1280定向界值仍有必要，不强改旧证据。默认无更小限制时 Normal1389、FEC1375、Game1373、Game+FEC1358。

后续028服务端按每session外层配置独立收窄；029 GUI只读展示内层；030不生成新的server级MTU公式。无用户内层普通输入，无重做 Rust record预算。H931真实两端 `41437214958` fixed客户端在Windows READY前退出仍 FAIL，H932+H933跨端 OS applied和DF/weaknet/CPU/p99仍 NOT_RUN。未重复派发旧矩阵。

```feature-impact
{"kind":"updated","ids":["path-mtu-budget"],"reason":"Synchronize sole MTU_CONTRACT v2 and later PLAN028/029/030/prompt/rollout to 1460 default outer complete IPv4 IP MTU; preserve explicit1500 max/goldens and source-scoped FAIL/NOT_RUN."}
```
