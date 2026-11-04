# PLAN028 H1098｜Windows 原 Go OS 切网冷 TLS 重试资格

[Action 41778793943](https://github.com/lly8666/wbd-next/actions/runs/41778793943) SUCCESS，独立解包工件13298470749；原Go donor a7a82db + overlay SOURCE `133d5e93ddbd2a311313cf8a80d3d3fc3fbb2430`，`assembly.json` SHA256 `6d8fd6f5...` 与六条实际Windows Go测试日志SHA256 `167fe8a2...`，6/6 PASS。实际OS选中物理ifindex/source4变化、旧 owner 精确 Stop 后，新 generation FakeTCP/TLS 若短暂超时可利用既有至多2次×2s冷重试（Game2/4同样），错密码包括Join timeout、用户Stop、首次连接、已Applied owner仍严格禁止重试。

同产品Go source `0a24ca98` 的 [Action 41778467840](https://github.com/lly8666/wbd-next/actions/runs/41778467840) 原生Go/WAL及Normal/Fixed/Auto/Game2/Game4各独立受限job全部SUCCESS。**绝非Windows真实物理网卡切换或Npcap出口换绑实际PASS**；后者与切网首包延迟、CPU/p99仍NOT_RUN。H998旧热缩MTU和旧ARM4FEC历史FAIL保留。

```feature-impact
{"kind":"updated","ids":["tls-auth-multiclient"],"reason":"H1098 six original Windows Go native path cold retry authorization unit PASS and same-product native WAL five mode PASS scoped; physical NIC rebind remains NOT_RUN."}
```
