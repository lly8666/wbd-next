# PLAN029 H2034｜GUI split-enable提示匹配Game4四lane冷接线

- H2033 [原Go入口提交d546da7](https://github.com/lly8666/wbd-next/commit/d546da726800241926f499188df75ee98b2da43c) 对`split-enable`允许Normal一lane及Game4四lane，Game2仍冷拒；[唯一原生Action43909402223](https://github.com/lly8666/wbd-next/actions/runs/43909402223) 当前正在编译/实网，Game4真实双出口与Stop**尚未取得PASS**。
- 复核源锁manifest的GUI `windows/gui/fields.json`仍称“Game2/4尚未接线”，与产品冷接线现状矛盾。H2034只修文案：Normal/Fixed/Auto和Game4四lane可配置，明确Game4真实业务**待验**、Game2仍拒绝、保存后下次连接生效。不修改GUI控件、Go/Rust数据面或网络授权。
- 同步唯一原Go assembly `windows/gui/fields.json`操作的补丁与完整生成结果Git blob `78412d44272a2e94640700e32ffc8b6a6faa0303`，保留真实manifest校验；本次无Game4原生触发标记，H2033在途Action不重派发。
```feature-impact
{"kind":"updated","ids":["dns-split-ipv6"],"reason":"H2034 align GUI helper wording with wired-but-unqualified original four-lane Game4 CN path while retaining Game2 fail closed, no network data plane changes."}
```
