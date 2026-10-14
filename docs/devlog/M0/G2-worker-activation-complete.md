# G2-001 M0 四角色正式激活与五crate接线验收

2026-10-14，用户明确继续并询问M0今后职责。答复：M0负责R系列阶段集成、共享接口/CI、跨角色合并、必要公共底座和阻断修复；M1–M4正式active后由各角色完成独立功能实现，不以M0代写全部工作，也不把四个active登记等同实际后台worker正在并发运行。

**交接**：本轮先读远端START_HERE/AGENTS/章程/project/registry/M0 cursor，checkpoint `b5768b2fe02f4678afaef0dd1353204b4161f4cc` 到HEAD `b6604f1405fb311ad63cc55dee5d1b8a65abc7be`仅一个cursor-only H，Governance38528572794 success，所有旧Actions结束，PR0，M0 active main epoch1/revision1；CLEAN。

**正式G2 SOURCE**：[83bd720](https://github.com/lly8666/wbd-next/commit/83bd720368b9be68b3c4c94d7462d20cf4d796db)。root`Cargo.toml`/`Cargo.lock`添加wbd-recovery（五crate），wbd-engine/src/lib.rs由M0发布runtime与memory两个挂点，实际测试scaffold仅`RECOVERY_ENGINE_READY=false`、`OWNER_RUNTIME_READY=false`、`ARENA_READY=false`。保留C ABI sentinel features0、Go生产V4 fail-closed、无新增第三方crate。main的registry revision1→2，M0 epoch1仍全球集成者；M1/2/3/4首次epoch1 active，分别固定branch`work/m1-r1-runtime`/`work/m2-r2-recovery`/`work/m3-r1-codec`/`work/m4-r1-platform`，只拥有互不相交的源码、自己的cursor/requests、devlog/evidence路径；共享root依赖/ABI/CI/类型由M0。M0 cursor的revision字段必须随registry在该实质S同步改为2，否则Governance在两笔提交之间无法验证，所以此处仅G2授权迁移，随后仍另推真正cursor-only H。

**远端四branch核实**：使用GitHub branches列表确认4个worker HEAD全部**精确等于83bd720**，另直接从每个分支分别读取`.governance/workstreams/Mi/cursor.json`，匹配role_id/branch/epoch1/revision2/sequence0/checkpoint null/progress planned/unverified true；不是因为“文档提到”就猜分支存在。四条各自push触发的Governance runs M1 [38531172259](https://github.com/lly8666/wbd-next/actions/runs/38531172259)、M2 [38531181545](https://github.com/lly8666/wbd-next/actions/runs/38531181545)、M3 [38531187784](https://github.com/lly8666/wbd-next/actions/runs/38531187784)、M4 [38531197940](https://github.com/lly8666/wbd-next/actions/runs/38531197940)全SUCCESS；正式接班时null checkpoint会刻意标RECOVERY_REQUIRED，worker须先自己完成首笔S/H后才可能CLEAN，不能把初始状态“恢复待确认”说成冲突。

**真实编译与证据**：同一SOURCE `83bd720...` [G2 bootstrap38531136641](https://github.com/lly8666/wbd-next/actions/runs/38531136641) attempt1 Linux Ubuntu24.04 x64，build job115743035789实际执行`cargo test --locked --workspace --no-run`，consumer job115743154391复核manifest所有源码+registry+cursor的SHA256以及Rust已编译测试二进制hash`928393d30db56245bf5ff6c0fc81b17742ce3a4e566f057759d49e635c24e16c`，不重编译直接运行bootstrap 1/1 PASS。build artifact11877532760 digest sha256:25c0af64cb8e992fc8f4e98b6d32f412602f62415ed73553418df9b9428a3844，consumer artifact11878102322 digest sha256:5d33ac1e67fcebf8bf6e3e54db34cef94c1f35e364d760f99b94ff23713e4586。静态资格audit38531136490 job115743035959 SUCCESS、main Governance38531136491 SUCCESS。历史R0 types38531136493、codec38531136439、LINK/FEC38531136481、record38531136555、native ABI38531136646、Windows+ARM cross38531136512、platform fake38531136489、旧Go control38531136499/vectors38531136524/TLS38531136468也都在**精确该SOURCE** success；Windows/ARM只cross，不能冒充目标native。

**未完成边界**：历史R0 10项scope gate仍属于原精确S，44架构ID中B01/R01/I01/C01/L01部分覆盖、39 NOT_RUN、完整ID零PASS；现G2只证明权限和脚手架。wbd-recovery crate不等于R2状态机，engine模块挂点不等于真实owner，M3真实AEAD/HP/ISA-L及M4真实平台驱动仍未开发，产品/性能/物理NOT_RUN、R0整体partial；Go生产V4仍DISABLED，原Go仓库没写过。四条worker尚无**实际首笔实现提交**，不会凭一个main聊天自动在四个会话中后台编程。

**done_when**：所有角色都正式active并有从同一基线的真实独立branch+cursor，范围/G2元数据正确，主线+每分支Governance及五crate源码编译+独立consumer与所有受影响R0回归success，精确证据与cursor-only H。已满足到收据阶段。

**唯一下一动作**：分派各worker的第一个真实原子任务并等待各自分支的S→Actions→H；M0仅负责共享API/依赖与组合回归、解决跨worker接口请求并序列整合R1 Normal/off等结果，生产V4必须另有真正资格门才能开放。
