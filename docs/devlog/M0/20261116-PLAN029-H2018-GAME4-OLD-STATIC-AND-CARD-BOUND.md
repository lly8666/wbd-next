# PLAN029 H2018｜旧静态断言与功能卡体积首个失败

- H2017原[Action43891174587](https://github.com/lly8666/wbd-next/actions/runs/43891174587) cheap断言只允许`if p029_direct or p029_p1_cn:`，新Game4 CN第三分支合法但未更新纯源断言；网络**NOT_RUN**。调整断言匹配三支及独立`--split-enable`。
- H2017 [功能目录Action43891174305](https://github.com/lly8666/wbd-next/actions/runs/43891174305) DNS card JSON>16KiB失败；仅紧凑格式、简化摘要和删除一条过期限制，控制卡尺寸为16372 UTF8 bytes。
- 无产品变更，保持原FAIL及H2018真正Game4 CN物理双出口四lane/owned Stop验收原始门。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2018 bounded DNS feature card and exact 3-branch Game4 CN static test; no product changes."}
```
