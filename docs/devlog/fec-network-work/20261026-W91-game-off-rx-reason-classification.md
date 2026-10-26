# W91｜Game OFF 接收错误分类最小补丁（等待精确原生验证）

- 基线：`8e13e86dcda0634951e648573a6563001d65868d`，此前同工位已经于 b5052654 因六个真实网络业务失败回撤未合格公开 Game+FEC；不恢复该候选、不覆盖他人回退。
- 根因定位：回退后的 OFF TX 空闲 sleep 已在取得 GameAdapter 锁**之前**执行（无须重复修）；TX 原生 send_one 仍持锁，是下一轮在正确基础上评估 TX/RX owner 拆锁的对象。
- 回退后的 `ReplayProtectedLaneRx::open_unique_in_place` 把 AEAD Authentication、可信 replay Duplicate/Retired、无效 record 全部压缩为 `Error::Crypto`。真实 W90 的 auth_rejected 不等同真正 AEAD 错误。
- 本补丁仅为已公开 OFF Game 路径分类拒绝：AEAD tag、invalid record、per-lane replay duplicate/old、scope/capacity/stopped/Game，以及匹配的低频 Stop 汇总；保留 `receive_diagnostics()` 接口为真正认证拒绝。单测：篡改 tag、认证重复、无效短记录。
- 旧 Action [Game2 fixed6 40209948309](https://github.com/lly8666/wbd-next/actions/runs/40209948309)、[Game4 fixed6 40209953632](https://github.com/lly8666/wbd-next/actions/runs/40209953632) 和 fixed0 负例永久保留；本次不是 fixed FEC 产品新资格，也未测性能。
- 完成资格：等待此精确 SHA 原生 ARM64 和真实 clean Game OFF TCP/UDP 后更新状态；Fixed FEC 后续只能在独立且已授权的可运行候选上恢复，不沿用旧产物。Windows TEMP_SKIPPED；capacity_stop=true；merge_ready=false。
