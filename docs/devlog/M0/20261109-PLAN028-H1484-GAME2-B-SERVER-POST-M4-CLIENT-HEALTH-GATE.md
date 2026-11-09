# PLAN028 H1484｜真实ARM64五用户收口：Normal B已恢复，Game2整组 B仍存在提前切换下行

新原始[ARM64 Action42626731886](https://github.com/lly8666/wbd-next/actions/runs/42626731886) SOURCE `c7c8e3da877a0c8f28152b766ffccd3d3baadb0c`：原始artifact13679196436 ZIP SHA256 `041fa9fca98b239c1945049a6650003c17f46bdc571450e835f61a1e6450e500`、CRC PASS。Go+Rust ARM双端 build、固定源manifest、L0、五客户端真实180秒、六个Stop都执行；Normal混合server B defer6/Auth Health promoted6/Go proof6，Alice两次新代真实提升。与上一个严重失效原始183170缺包不同，当前全方向仅Carol Game2下行5个永久缺失、其余所有用户双向UDP均零缺。**硬门仍FAIL**，不认为修好。

按原始10ms桶消去未来迟到包：Carol下行 51.70s +3、159.41s +2，分别贴合实际Game2 Gen2/Gen3换代；服务端共享TUN lease Carol offered=55217/direct=55217、全局 queue_full=0/retired=0/age=0、该租约峰值待发0，客户端旧代在途接收和最终owned Stop真实执行。这些是相关性，不是逐包RAW到达结论。

查当前真实调用链：`v4_embedded_go.rs::wbd_m0_embedded_go_game_group_loop_start` 对 **server** Game2/4整组B仍在本地M4建立后马上把 /32 发送入口换给B，而client B此时尚可能未启动完整RAW RX；相反Normal B已在server等待真实客户端M4 Auth Health kind0才发布。Game client已有等待**服务端**真实Commit门，但这是单向证明，不能保护server下行。Game本身已有 authenticated activity/Health TX，无需新包种/固定探针。

本轮最小补齐：Game整组Native M4仅在完成RX/TX worker后各端发一次原有加密kind0 cold Health，恢复对server读回经过AEAD/PN的client kind0；server共享TUN B在A存活时延迟路由发布；Go mixed 443 单事件循环中，针对实际同principal+tunnel已认证完整Game B，异步最多5s只读native认证Health，成功才在Rust/Go发布B+旧A随机10–20s RX grace/精确Stop，失败只Stop B；Game4单lane热替换与别的client不碰。修正同epoch A也会被精确退休（不能被active map覆盖漏Stop）。添加确定性旧代路由、没Health不可发布、Health后旧Stop不伤B 的L0测试，并把真实ARM verifier扩展要求Carol Game2 2次B-defer/peer Health/promote，原业务全向零缺及所有Stop；**候选仍NOT_RUN，等真实原生结果后再判**。

保持现有外层唯一TUN TX route、不做跨代业务双发，不增稳态头、Go热泵或新定时探针；原失败、Windows专项/Android未跑原样保留。PLAN028 IN_PROGRESS。

```feature-impact
{"kind":"none","ids":[],"reason":"Repair an actual PLAN028 original TLS/Game2/4 cold readiness wiring gap; reuse native authenticated control, no new feature or protocol."}
```
