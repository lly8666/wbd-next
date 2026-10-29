# PLAN027 H403｜回收 H401 ACK/SACK 原生验证
2026-10-30。H401 SOURCE `c8dad61048d532b3e6d7eb11f94fb36ffa1d6a8e` [native40946233170](https://github.com/lly8666/wbd-next/actions/runs/40946233170) 全六组 SUCCESS：platform **95/95**（两项新 ACK/SACK checksum/能力/MTU/隔离测试）、engine **134/134**、kernel6、receipt11、fec3、normal3。共享 build artifact 12930150538、manifest `3f5d5de11bdecd11adc24cd1d9412636a07904dbafe8e231b8d614658a71c5e4`，binary/log hash 与 job ID 见 [H403 evidence](../../evidence/M0/PLAN027-H403-ACK-SACK-WIRE-SOURCE-NATIVE-RESULTS-20261030.json)。
H400 原编译 FAIL40945968960 与 H401 治理 feature-impact 缺 ids:[] FAIL40946233545 保留；H402 [governance40946398609](https://github.com/lly8666/wbd-next/actions/runs/40946398609) 修复后 SUCCESS。H401 Windows/Linux preflight40946233322 仍在途，不能据此称真实双端 PASS。
**此验证仍仅平台纯 ACK/SACK wire**；Windows/Linux 原始 owner、实际 ACK/SACK 修复、低频 Quality、线上 M2 Receipt 退役、A/B/C/长测均未完成。继续接线，不重复同源 native。

```feature-impact
{"kind":"updated","ids":["outer-opportunistic-repair"],"reason":"Link exact-source H401 strict ACK/SACK wire native PASS while retaining product owner/Receipt/A/B/C NOT_RUN."}
```
