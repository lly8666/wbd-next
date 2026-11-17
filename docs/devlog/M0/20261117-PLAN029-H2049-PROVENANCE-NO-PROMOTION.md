# PLAN029 H2049｜用户缩减范围 SOURCE 台账与当前未验边界

- 只汇总用户最新要求（GUI真实起网/有效值、TC/bootstrap/FakeIP writer、五类资源满、默认1460和padding source）；排除IPv6/P1/P2旧尾延迟/CDN同IP专项及028旧矩阵。
- 保留每条历史真实证据 SOURCE+原Action、Normal1460和Game4 legacy1400严格分开、H2031 Normal padding真实包长和原密文不解密限制。异步FakeIP writer小额度Windows/Linux纯测属于SOURCE_LOCKED_RUST_PURE_PASS，不能替代物理慢盘跨流。
- H2045 GUI初验真实Action FAIL 首个边界为夹具H1845原CLI被替成GUI父argv，真实产品网络NOT_RUN；H2048修正后在途，绝不提前记GUI OS Applied PASS。H2047物理TC同端点在途，未确认 TCP53或重连。五类资源现只有Direct hard8真原生证据，其他以组件/NOT_RUN区分；Off/on CPU/RSS和padding GUI effective仍 NOT_RUN。
- 本档为源锁清单而非PLAN029全面PASS或完工声明；待在途结果精确更正，不重复派发。

```feature-impact
{"kind":"updated","ids":["gui-config-feedback","startup-flow-padding"],"reason":"Source-specific user-scoped 029 ledger preserves H2045 first FAIL and H2031 passing padding, distinguishes pending real GUI and off/on cost."}
```
