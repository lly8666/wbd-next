# PLAN027 H460｜修复功能卡与真实Auto单场景回归

原始证据H455 B Auto Action40994443303: Windows TX385 / RX0, Linux TX100 / RX27，Linux TX CPU41.8s/约42s。H459纠正仅当真实PN进入Auto START窗口才提供CLOSE deadline，防止RX/TUN饥饿的0ms busy loop。H459特性声明了fec-auto但未改card，main治理Action40995823454 Feature catalog明确红项；本批更新现有card摘要，紧凑JSON实际UTF8小于16KiB，保留原功能边界和所有历史证据。

新一次性Actions dispatcher：本次H460提交且main SHA与checkout一致才能启动单独`public_mode=auto` Windows原Go TLS / Rust Npcap↔Linux raw/TUN真实B；没有旧H455二进制复用（Rust产品源码变化），只一Action一实测场景，不重复H458已在途A2/A3三条与B Fixed。真实first arrival、CPU/Stop/MTU、低频质量反馈都以新run判断，不从纯单测或短例宣称PASS。

PLAN027 A4/A5、B生命周期、C逐级/长测仍未完成。

```feature-impact
{"kind":"updated","ids":["fec-auto"],"reason":"Real Linux Auto expired-CLOSE deadline fix documented, new full B Auto native test pending."}
```
