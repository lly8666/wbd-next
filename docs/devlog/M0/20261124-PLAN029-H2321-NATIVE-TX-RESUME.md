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
