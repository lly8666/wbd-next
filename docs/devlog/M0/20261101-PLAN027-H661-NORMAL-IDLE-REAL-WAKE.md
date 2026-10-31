# PLAN027 H661 — Native Normal no-payload 108.49s and original kernel wake

[Real dual-native Action41223668774](https://github.com/lly8666/wbd-next/actions/runs/41223668774), original PRODUCT SOURCE `dc191cf5686ddff2e433312b8ec2258954bd018f` H656 manifest and harness HEAD ba29, 105s requested payload idle, **108.49s measured**, original Windows Go TLS Npcap/Wintun + Linux Rust raw/TUN owners stayed alive; subsequently fresh dual native UDP and TCP and owned Stop passed. 10Mbps each direction /25ms/0% measured first1.0/1.0, Linux TUN dropped0 both directions, whole Windows Go+Rust CPU2.407% one core, peak RSS41,971,712B. Original scenario SHA f08884d64decfbcd70284417c720283fa0690987bcacd65ec3a252fe6e1777fd.

Authenticated per-15s Health record count was **not explicitly measured**; no-payload idle is not no-authentication dead90s. The historical B106 bilateral re-auth canceled runs cannot be declared PASS from this. FEC and blackhole20/Fixed idle105 source-reused separate native Actions remain in flight. Do not promote physical or one-way p99.

```feature-impact
{"kind":"updated","ids":["generation-stop"],"reason":"Document source-locked native Normal idle108.49s positive and accurate Health/dead reauth limitations, with no runtime modification."}
```
