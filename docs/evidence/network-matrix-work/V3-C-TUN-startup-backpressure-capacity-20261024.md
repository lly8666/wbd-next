# V3-C cold-start TUN local loss: bounded admission and backpressure decision

This is an **existing workstream evidence note**, not a separate handoff system. Source of truth remains `status.json` and `NETWORK_CURRENT_PLAN.md`. All execution tests run solely through Actions on `experiment/network-matrix-tuning`.

## Direct observations

- One ARM64 VM, 0% netem, single inner TCP C→S 500Mbps, RTT ≈400ms, Normal/off; original product source `b8dfc570c8d30098ab6b5a6d98165e22967a56a0`.
- Native Action **40039575725**, SHA256-verified artifact **12538359391** (ZIP `2a86c05b90bee15d34887810618448a153b2e99f9a89ba6507f9447f4d21893f`), exact source `cf4a8f2ee9b6d9588b5ddf9d87e231701bc679fd`.
- A and B both have real TUN root `fq`, verified link `txqueuelen=1024` vs `2048`. Both deliver **500.0003584Mbps** for 60s steady, kernel TCP retrans steady=0, source TUN steady drops=0, p99 first arrival 202.9/203.0ms, TCP backpressure 0. This is a **steady-state scoped PASS**.
- **Warmup is NOT lossless**: client TUN drops A **7471**, B **7544**; TCP cumulative retrans observed by first steady sample A **7468**, B **7541**. Read from `network-snapshots.json`, not extrapolated from packets sent.
- M1 ownership peak remains **32 of 2048**, so increasing the M1 pool is not supported. The TUN `txqueuelen` increase also failed to reduce warmup local drops. Do not use these as a generic recipe.
- The ARM runner kernel is `6.17.0-1022-azure`, 4 logical CPUs; during full-rate steady host CPU PSI-some mean ≈27.7%, a contention warning. Product CPU ~46.3s client +64.0s server over 60s. Do not claim CPU savings or physical deployment qualification.

## Bounded causes, not guesses

At 500Mbps / 1377B TCP MSS, approximately **45,389 source TCP segments/s**. A 1024-packet queue holds ≈22.6ms at that average, and 2048 ≈45.1ms, ignoring TCP ACK/control and burstiness. But cumulative **~7.5k** drops only in cold 20s despite both queue sizes, so the causal boundary is *not uniquely established* by queue length. Distinguish TUN internal `ptr_ring` overflow from root `fq` drop/flow_limit (which defaults to 100 per flow), other upstream kernel pacing or producer/consumer scheduling. New test controller snapshots `tc -s -j qdisc show dev wbntun0` to ground actual qdisc counts.

Newer Linux TUN has an opt-in `IFF_BACKPRESSURE` (0x0080) which can stop the internal ring rather than tail-drop and let attached qdisc apply backpressure. **Do not assume Linux 6.17 supports it.** Before any product use, `TUNGETFEATURES` (not a constant inferred from headers), actual `TUNGETIFF` readback and attached qdisc and kernel version must confirm support. Do not pretend to enable it on unsupported production kernels, silently set unknown bits, or relax authenticated feedback/repair. Linux kernel docs: https://docs.kernel.org/networking/tuntap.html ; implementation flag in newer Linux source: https://github.com/torvalds/linux/blob/master/include/uapi/linux/if_tun.h

## First bounded source-side candidate

Commit `ae38b36048024f18df01cbdad171cffdc7dd2da7` changes **only** original Rust source TUN intake: after four genuine immediately-ready reads, borrow up to eight original-generation M1 slabs under one session lock, then read via already-nonblocking TUN FD. Unused loans are returned **before M3/M4**. Sparse packets retain single-loan fast path. The original **16-slot authenticated receipt reserve**, total 2048 M1 backing, one-repair immutable policy, 9%/10% wire budget, MTU/MSS/authentication and Stop are unchanged. No new global hot lock, unbounded queue, packet side table or eager shadow clone. **NOT_VERIFIED** until native ARM64 build (run 40043419093) succeeds.

The next valid test is exactly ONE same-VM sequential original-source A/B, same full 500Mbps warmup+steady, same `fq` and `txqueuelen=1024`, with **strict startup-and-steady source TUN zero-drop acceptance**. Both throughput and input pacing are fully counted: require delivered≥475Mbps, p99≤400ms, no locally lost app, no sustained host misqualification, proper Stop. Never infer packet integrity merely from steady delivered rate.

If B still has cold-start TUN loss, record `V3-C-STARTUP_OPEN`, stop heavier repeated load tests, and design an explicitly bounded **separate TUN intake / AEAD+raw submission** producer-consumer schedule. A practical *initial engineering bound* is a fixed 512-slot SPSC of already-owned 2KiB original-generation slabs (~1MiB) at a 45kpps design point (≈11ms of buffering); start by measuring source servicing gaps and use 16 receipt slots as a hard invariant. All slots must come from existing memory ownership, no secondary untracked packet copy, tail-drop hidden from metrics, fabricated TCP ACK, unbounded backlog or priority inversion. This is a design starting point, not proof that 512 is sufficient; sustained overload must be surfaced explicitly. New kernel backpressure is a separately version-gated possibility, not a substitute for measurements.

## Test acceptance corrected

The harness now supports `acceptance.require_zero_source_tun_drops_full_run=true`, collecting *both warmup and steady* `wbntun0` kernel TX-drop deltas. A missing readback fails the strict zero-loss gate; every dropped packet counts, even if TCP later retransmits and application bytes eventually arrive. This gate is opt-in to avoid silently reclassifying historical scoped reports. New tests verify schema rejection and exact sample delta.
