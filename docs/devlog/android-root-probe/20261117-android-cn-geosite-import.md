# Android Root CN geosite 完整离线快照预接入（2026-11-17）

原分支 `experiment/android-temp-root-probe`。继 [Action43909181856](https://github.com/lly8666/wbd-next/actions/runs/43909181856) 已证明 18/18 纯策略、10/10 隔离 UID 内核路由、App UI真实添加/保存/Root原生读回之后，进一步覆盖 `.com/.net` 等中国服务域名。此阶段只处理 **CN DNS QNAME 分类**，不基于域名伪装任何 DNS A/FakeIP，不把域名反查用于 DATA；实际数据出口严格由真实解析 IP 和每App split/global 模式决定。

## 新依赖与固定来源

- 规则源：MIT 许可的 `v2fly/domain-list-community` 固定 commit `41504eae2a11f305fe88cfc605cf6c105a80bf5a`，`data/geolocation-cn`；明确保留上游 LICENSE，并将 SNAPSHOT zip/文本 SHA256、include 关联项数/规则类型数写到APK `cn-geosite-provenance.json`。GitHub Action 从 `codeload.github.com/v2fly/domain-list-community/zip/<固定SHA>` 构建，不能在手机上静默自动刷新。
- `cn-geosite-snapshot.py` 全文件解析 `include` 递归、`@required` / `@-excluded` 属性与 `&affiliation`，对直接和 include 继承规则做去重，区分 `domain/full/keyword/regexp` 四类，不把非 suffix 当 suffix。拒绝未知源语法、引用缺失、循环、源文件损坏及异常体积。
- 独立 Rust `cn_geosite.rs` 从App私有已fsync+原子替换文件读规则，校验SHA256，编译 exact/suffix HashSet、keyword集合与RegexSet；DNS按标签数量/关键词数匹配，**不在IPv4数据包路径调用域名匹配**。无FakeIP。若来源正则与Rust regex无法等价编译则**FAIL_CLOSED**而不是忽略。
- `SplitSettingsActivity` 每次保存先取APK资产与来源锁定摘要比对，再写 `wbd-cn-geosite.txt` 并保存摘要字段到原配置；`splitvalidate` 真 KSU Root重新核验原文件SHA，编译所有规则，检查代表性 `baidu.com`、`qq.com` 子域为CN DNS，并在 split 下保证任意海外A仍走Tunnel。原 `wbd-split-validation.json` 输出总数/各规则类型/摘要，`installed=false` 保证没有真实主网络操作。

## 不扩大之前实测结论

- Android APK+KSU AVD CI 将验证新增的规则库生成、真实性、应用写盘→Root重新读回、双ABI、旧18纯策略/10内核选路/旧TUN恢复；CI不联网向真实CN DNS服务做查询，不意味着生产DNS worker、Android netd主namespace Apply、完整WBD TLS/数据面、真机热点USB或物理IPv6完工。
- 即使 geolocation-cn 是完整上游列表，也不能保证所有中国域名或所有IP归属永远准确，需要前台有界更新/来源验证与用户自定义。

```feature-impact
{"kind":"updated","ids":["android-temp-root-probe"],"reason":"Bundle pinned MIT geolocation-cn full include/attribute graph and match domain/full/keyword/regex only for Android Root DNS classification; App atomically saves and Root validates content hash, no FakeIP or production netd Apply."}
```
