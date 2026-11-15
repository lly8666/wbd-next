# PLAN029 H1929｜真实治理hot-read预算被32B超越，缩短M0 cursor消除无用红灯

- H1928 evidence、功能卡、原签名H1927网络业务皆正确；[governance Action43722873267](https://github.com/lly8666/wbd-next/actions/runs/43722873267) **FAIL**。原生的feature catalog和role identity测试通过，但`tools/governance.py validate`的真实结果 `combined hot byte budget exceeded: 32800`，policy `max_hot_bytes=32768`，超出32B；不是可忽略的假红。
- 根因是当前活动M0 cursor相对上一版本的结论段重复过长，与`AGENTS.md`、`PROJECT_CHARTER.md`、registry、`START_HERE.md`、特征README、M0提示词共同达到全局限额。H1929**只压缩当前游标4段冗词**，保留相同`last_tested_source`、唯一已签名证据ref、全部历史context refs、未验证完整PLAN029状态；不提高上限、不删除历史。修正应同时通过feature catalog与governance。
- H1927原签名 Action43721447384原Go/Rust Wintun/Npcap/WSL2 4MiB+384小TCP A-B-B-A+Tunnel96B UDP/Stop **PASS**，H1926 CPU栈优化**功能验证通过、CPU减幅未量化**。本H1929不更改产品/实验夹具，不重复派发原生。
