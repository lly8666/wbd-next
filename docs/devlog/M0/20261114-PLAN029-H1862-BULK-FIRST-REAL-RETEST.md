# PLAN029 H1862｜一次真实4MiB无人工Pacing P2，和H1861纯Tunnel P1分开

- H1860 SOURCE `b6f87cee` [Action43615797731](https://github.com/lly8666/wbd-next/actions/runs/43615797731) 编译/签名准备及WSL2通过，Linux角色因第4参数与旧入口检查冲突在绑定TCP listener之前退出，故4MiB真实交付 **NOT_RUN**；只精确owned finally恢复PASS。此源失败不能用作TCP性能失败证据。
- H1861 SOURCE `905e1cef` 已加入经单元逻辑验证的Mode::All非DNS合法普通L3 pin-free fastpath，并修夹具`len(sys.argv) in (4,5)`、`p2bulk/p2paced`的跨WSL两侧一致性及Windows高分辨率`perf_counter`。本批不改算法/配置/Defender/WSL，**只靠现有工作流**以`[plan029-v3-real-p2-bulk]`首次真实比较物理TCP4MiB与Direct TCP4MiB，整段持续Tunnel小UDP、SHA/半关闭、p99、最长空洞和owned Stop。
- H1861独立单VM P1 A/B在途，绝不在一个Action混测；只收结果，不重复dispatch。契约§5追加最新H1856真正Npcap根因修复和H1859 P1 CPU回退，保留历史失败、D1–D5/P1–P2退出及Game4/GUI/IPv6待办。
- 本SOURCE新Action结果当前**NOT_RUN**，029仍IN_PROGRESS，不提前交付。

```feature-impact
{"kind":"none","ids":[],"reason":"One separate native P2 bulk source dispatch using already-corrected 4th arg and high resolution clock; update stale §5 investigation evidence, no product code change."}
```
