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
