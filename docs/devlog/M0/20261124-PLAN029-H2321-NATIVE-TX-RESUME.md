# M0 PLAN029 P0 当前接续：H2318–H2321

用户2026-11-24恢复M0读写开发授权，性能优先，先修原有热路径而非反复扫描TX batch参数；同时收束历史Actions误触发。现役分支 `experiment/m0-029-throughput-arm-fair`，PR #68，实验分支本次冻结源 [bb063c9932ef3d4a7873c99a6f4bb38248acbd9a](https://github.com/lly8666/wbd-next/commit/bb063c9932ef3d4a7873c99a6f4bb38248acbd9a)。main 产品不变，本记录只用于接班。

| 增量 | 实际状态 |
|---|---|
| [H2318 0627806](https://github.com/lly8666/wbd-next/commit/062780613a3c266f6aa29438b609348d7fa4c54a) | Windows native source复用最终frame、消除中间密文复制。源锁Windows [45305575290](https://github.com/lly8666/wbd-next/actions/runs/45305575290) 与 [45305575316](https://github.com/lly8666/wbd-next/actions/runs/45305575316) 通过；实际吞吐未验。 |
| [H2319 fc94334](https://github.com/lly8666/wbd-next/commit/fc94334450225c1d908c9375535387f15a41cdc4) | 49个历史实验独立request path，保留原手动/marker/验收；治理 [45307484579](https://github.com/lly8666/wbd-next/actions/runs/45307484579) 和维护 [45307484562](https://github.com/lly8666/wbd-next/actions/runs/45307484562) PASS。H2320实际push仅4个治理和原生单元工作流，没有历史全矩阵误触发。 |
| [H2320 a0a56bf](https://github.com/lly8666/wbd-next/commit/a0a56bf275a7313256f69fd8031071e584946b48) | Normal/off 真 M1 8/16 ready batch，每批一个 budget/time/LoanBatch，沿用既有32 ready queue。 [45307622202](https://github.com/lly8666/wbd-next/actions/runs/45307622202) Windows 两组各66平台单元PASS、实际新16→1→8批处理1/1 PASS、两个feature编译PASS；[45307622223](https://github.com/lly8666/wbd-next/actions/runs/45307622223) maximum unit PASS。治理与维护 [45307622274](https://github.com/lly8666/wbd-next/actions/runs/45307622274)/[45307622253](https://github.com/lly8666/wbd-next/actions/runs/45307622253) PASS。不是性能PASS。 |
| [H2321 bb063c9](https://github.com/lly8666/wbd-next/commit/bb063c9932ef3d4a7873c99a6f4bb38248acbd9a) | 新鲜当前Go/ARM及A/B Rust DLL构建；真三runner A/B/A′，[Action 45307927201](https://github.com/lly8666/wbd-next/actions/runs/45307927201) static PASS，Windows/ARM构建 in_progress（本记录创建时）；网络与吞吐未有结果。 |

H2321 A/A′为7222b4739443dbb7ff9b322f186dcf651b54490f，B为bb063c9932ef3d4a7873c99a6f4bb38248acbd9a；全部TX8/NPF16KiB，FEC OFF、repair OFF、0%loss，旧夹具B_tx16仅历史stage ID。先读取在途 Action 首个异常或完整远端有效字节/CPU/GiB/P99/Stop，禁止重复dispatch、跨SOURCE借PASS。旧H2292等归档工作流仍保持各自旧源锁；新H2321不依赖旧二进制。H2321只比较累计优化，不是单项归因或600–800Mbps物理资格。P1/P2及Game最终Windows CPU仍未验，原专项范围收口不重开。

下一生产增量依据结果再决定：原生TX空控制重复owner锁、firstsend settlement逐包时钟与pending操作、NPF最终队列复制。优先解决证实的处理成本，不重刷TX16参数。已有窗口、FEC与Linux准入反例照旧。

## H2323：实际构建故障及定向重试

H2321 首次 Action 45307927201 static PASS，但 Windows fresh Go EXE 构建在 H2214 CLI flag 声明检查失败，未执行网络腿，非性能 FAIL。核对分支 manifest 的 main_windows.go 70 个 patch 与 main 的前70个完全相同，遗漏第71个原有 TLSVerifyServer flag 声明；直接复用 main 已有第71个 patch 与 result_blob 3238f8819563c51bc34c33f5e884f9d36c421231，不变更默认行为或另设机制。实验分支 H2323 [6fa10d75](https://github.com/lly8666/wbd-next/commit/6fa10d75e3b7f23f909252e2737948911d3eb64c) 修复装配，并限定 A/B 共享该同一当前 Go EXE、原三 Rust 文件仍为唯一 Rust 差异。独立 request path 已触发 [45308263564](https://github.com/lly8666/wbd-next/actions/runs/45308263564)，当前 pending；只查此 run，不重复派发。旧 ARM 构建结果不借给新源。真实吞吐未验。

## H2326–H2327：真实收益与独立下一增量

H2323 Action [45308263564](https://github.com/lly8666/wbd-next/actions/runs/45308263564) 六个实际job全部PASS；同VM A/B/A′ 真实ARM接收192.036/251.586/160.973 Mbps，Windows CPU/GiB 30.1517/20.4012/29.6310 秒，P99 250/204/313ms，三腿各160 echo、0 late>1s、0 NPF short、owned Stop PASS。B vs A/A′均值吞吐 +42.54%、CPU/GiB -31.75%；基线漂移存在，单组范围收益，不是600–800资格或默认推广。精确原日志三行及每腿DLL SHA/编译SOURCE/NPF统计归档于 docs/evidence/M0/20261124-H2323-WIN-ARM-FIRSTSEND-AB.json。H2323治理失败为遗漏feature-impact；H2326新devlog补齐，精确治理 [45310696184](https://github.com/lly8666/wbd-next/actions/runs/45310696184) 与维护 [45310696198](https://github.com/lly8666/wbd-next/actions/runs/45310696198) PASS，旧红灯不改写。

[H2326 e85c63b](https://github.com/lly8666/wbd-next/commit/e85c63b1e11f41142528a8230d5497b4f1c010df) 合并pending验证删除为单次BTreeMap搜索、OFF首发不读无用时钟、feedback/repair同一次owner锁顺序检查；不持锁发NPF、无新队列/线程。原生完整owner模块回归 [45310696203](https://github.com/lly8666/wbd-next/actions/runs/45310696203) 与Fixed maximum [45310696193](https://github.com/lly8666/wbd-next/actions/runs/45310696193) 在途。
[H2327 c828c45](https://github.com/lly8666/wbd-next/commit/c828c4561917151f82385edfbe21ada60849c6df) 复用原明确请求入口，两个独立真三runner A/B/A′；A/A′锁6fa10d7，B锁c828c45，仅两个Windows Rust文件差异，同一当前Go/ARM、TX8/NPF16KiB、FEC/repair OFF。 [45310787767](https://github.com/lly8666/wbd-next/actions/runs/45310787767) static PASS、构建在途；治理 [45310787620](https://github.com/lly8666/wbd-next/actions/runs/45310787620) PASS。H2326收益未知，不重复计入旧42.5%；先查已在途的精确run，禁止重复派发。下一项优先研究NPF最终队列复制而非再堆batch参数。

## H2330–H2332：连续去除真正热路径工作

H2326 原生完整 owner 回归 [45310696203](https://github.com/lly8666/wbd-next/actions/runs/45310696203) 最终PASS（25 owner、两套66 platform）；Maximum [45310696193](https://github.com/lly8666/wbd-next/actions/runs/45310696193) PASS。H2327 双组真实对照 [45310787767](https://github.com/lly8666/wbd-next/actions/runs/45310787767) 静态/Windows双DLL/ARM fresh build已完成，六网络runner在途；不提前归因或重复派发。

[H2330 0530730](https://github.com/lly8666/wbd-next/commit/0530730161a5ebf0dd2bca34b25ae972837447b5) Normal fitting ready batch 直接写入既有Npcap sendqueue并原地构头，减少一次完整frame复制，复用原transmit/trace/prefix分类。原生 [45311324747](https://github.com/lly8666/wbd-next/actions/runs/45311324747) PASS（两套67 platform、直接queue混合字节/短返回/复用实际测试、25 owner和两profile编译）；[45311324728](https://github.com/lly8666/wbd-next/actions/runs/45311324728) Fixed Maximum PASS，[45311324738](https://github.com/lly8666/wbd-next/actions/runs/45311324738) governance PASS。真实收益未验。
[H2331 e8d4d3b](https://github.com/lly8666/wbd-next/commit/e8d4d3bef9a623d6d6053b0aa5d1234391e5fdc9) 对照只含H2330，A/A′锁c828c45，B锁e8d4d3b。两独立组，TX8/16KiB、FEC/repair OFF、同current Go/ARM。 [45311438312](https://github.com/lly8666/wbd-next/actions/runs/45311438312) pending，和H2327同workflow concurrency，禁止第三个request覆盖在途pending；治理/维护45311438233/45311438214 PASS。
[H2332 6873c98](https://github.com/lly8666/wbd-next/commit/6873c98a876f2cb23b76449b05c95e01e27ad864) Normal FEC OFF且repair OFF的同步TX原M1 LoanBatch跨NPF调用并在返回后回收，去掉每包pending树插删和额外冻结引用，原Go ABI、repair ON、Fixed/Auto/Game不变。新增实际owner 16/1/8测试；[45311680513](https://github.com/lly8666/wbd-next/actions/runs/45311680513) 原生回归在途、[45311680368](https://github.com/lly8666/wbd-next/actions/runs/45311680368) maximum在途、45311680548 governance PASS。独立性能请求尚未发，等H2331队列槽开始/完成再派，防止覆盖现有pending。当前远端实验HEAD 6873c98；H2332不是此前两次AB candidate。

### P0全局容量边界及后续决策

当前H2286真实签名产品夹具仍用Windows WSL2转发 + ARM relay + ARM TUN，外层1280（不是项目默认1460）。历史H2285裸Windows经WSL2同类链路两组468.211/496.194Mbps，H2284不经WSL2的裸8流relay两组680.275/995.493Mbps；不同runner/日期，不能作为本次精确上限或产品相对损耗。但足以说明600–800目标必须做同VM同路由裸链路容量校准，不能把当前夹具的较低容量变成产品结论。后续高线资格应先用H2285真实裸OS路径与同VM产品路径对照，在达到实际目标的下层路径上测产品，而非改MTU破坏现有underlay；若达不到则环境未资格。四流2MiB场景继续用于独立热路径增量比较，不与新的高线供给/MTU/route因素混合。先结算H2327、H2331、H2332，只保留有净收益且不牺牲真实业务的增量。之后进一步研究Wintun到M1明文重复复制（现有Arena由owner独占，不能简单拆共享所有权或持Wintun借用跨锁等待）、repair ON每包global credit lock及固定FEC保护效率。不得重复已否决参数扫描，也不把候选源层面操作减少说成实测收益。
