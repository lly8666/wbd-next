# PLAN029 H2030｜修真正残留的Game4 CN场景NameError并触发原生网络
- 复核main时发现H2020曾记录后移`p029_game4_cn`排他检查，但随后H2021工具文件旧内容覆盖，导致当前main行46仍在定义`p029_p2/cache/pressure`之前读取；H2023[Action43894787329](https://github.com/lly8666/wbd-next/actions/runs/43894787329) 正是因此在0s时NameError，非Game4网络失败。
- H2030明确删除旧早期检查，恢复至`p029_smalltcp`等所有p029 flags初始化之后；只在合法game4单独场景打印`PLAN029_H2030_GAME4_CN_EXCLUSIVE_REAL_FOUR_LANE_SCENE_ARMED`。不变Go/Rust四TLS lane/原M1/OS WAL或原GameAdapter。
- H2029只有docs/cursor，不在`m0-wl-public-normal-full.yml`受监控push paths中，因此没调度native。H2030在受监控`tools/m0_wl_public_normal_e2e.py`修改并携带独立`[plan029-game4-cn-real]`真实触发门，和H2028 Normal随机20..30条/2..3s真实pcap不同场景。
```feature-impact
{"kind":"none","ids":[],"reason":"H2030 restore correct actual Game4 CN scene guard order and monitored tool-path trigger; Go/Rust data-plane unchanged."}
```
