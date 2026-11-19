# PLAN029 H2163｜WinGUI设置覆盖审计与过时Game帮助更正

- 当前基线 `4abc23a1d3bdfe1136634de61aac58c73c47d495`。H1650实际WinForms 49可见字段/354项配置和按钮VM PASS但模拟会话；H2059 GUI flows→原Rust M1 NPF真实PASS；H2105 CN旧配置迁移PASS；H2135真实原GUI高级→普通→all三代OS/DNS/业务及owned Stop PASS；H2162 Game2/4 FEC off/fixed × 五政策20/20真实PASS_SCOPED。分别保持原SOURCE，不混为新SOURCE全功能PASS。
- GUI“网络”页已有分流总开关、route-mode、CN域名FakeIP开关/规则文件、中国IP、Direct-flow上限、双DNS；“传输”页FEC/MTU/repair/startup-padding，“服务器/连接/状态”页域名/凭据/启动/断开和readback。AAAA NODATA、受管IPv6丢弃是自动政策而非应额外添加的开关。
- 正式manifest派生GUI字段hint旧写“Game2仍拒绝”，PARAMETERS帮助称Game2/4 CN not wired，与H2162冲突。仅改两处文字及功能卡现行描述。逐项复用原Git blob重放32/13个替换：原结果SHA精确匹配，更新文字的结果blob分别为 `e7afe322bfd5c7b1d77308caab04706e82891ec3`、`4aa96a983817595e1a7409c95754651bf67ce4d6`，同步manifest。没有改Go/Rust/ABI/FEC/热路径。
- **本轮新GUI SOURCE编译/真Windows验证NOT_RUN**；原H2135、H2162签名资格仍限于各自SOURCE。029/029B日常PASS_SCOPED、完整技术D1–D5/P1–P2和029B§6–7 OPEN，Game padding未接、旧Linux主动入站Windows TCP未验、全宿主IPv6不可承诺，P-B2与小TCP p99未测；历史FAIL不抹除，无新Action派发，030未开。

```feature-impact
{"kind":"updated","ids":["dns-split-ipv6","gui-config-feedback"],"reason":"Correct stale derived GUI and PARAMETERS Game2/4 CN unsupported help against exact H2162 signed scoped result; no new native qualification."}
```
