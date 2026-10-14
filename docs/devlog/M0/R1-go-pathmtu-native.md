# M0 · R1 pinned original Go pathmtu native oracle (2026-10-14)

**Owner / atom:** M0 R1-M0-GO-PATHMTU-001. **Source:** the commit introducing this workflow (to be confirmed by remote ref). **Initial S status:** Actions PENDING at time of workflow push (preserved). **Observed after run:** exact source `e8599f7ad512e9e4ad0e2ac4cbb58cb819891a40`, Actions [38543117078](https://github.com/lly8666/wbd-next/actions/runs/38543117078) attempt 1 build115782469803/consume115782651812 **SUCCESS**; old native `internal/pathmtu` **10 top-level Go tests PASS**, seven required names present, exit=0. Compiled binary SHA256 `82c271c20fe222b31a377c0d0674257d45ac30af42769a0e6ada3935020411ba`; build artifact 11883381295 and result artifact 11883391413. Same-SOURCE Governance [38543117065](https://github.com/lly8666/wbd-next/actions/runs/38543117065) SUCCESS. Evidence: `docs/evidence/M0/R1-go-pathmtu-native.json`. This does not test M3 Rust against Go in the same binary.

## Why now

Main M0 cursor seq21/checkpoint `7087997543d149091f4f20021ab34570d07112dd` and live HEAD `edb275dee8745ced8f45fcf15b362b9044589e14` had only one cursor-only H, Governance 38540461976 SUCCESS. M1 and M4 remain isolated, M2 pure receipt partial, M3 seq2 FrameBudget native Rust SOURCE `3aa121e4c10a80c4175ccfb057f3e64b01e4b382` 6/6 success but **no original Go pathmtu native execution**. M3 documented the request in `docs/devlog/M3/M0-REQUEST-AEAD-AND-ORACLE.md` on its separate branch. This M0-owned workflow closes only that native Go oracle gap. It does not add third-party crates, touch a worker ref or implement crypto.

## Frozen contract / Actions plan

Original source: `lly8666/wobuzhidao@a7a82db31fe736ffedee330795a3234d358f1984`, `internal/pathmtu/{budget.go,budget_test.go}`, Go 1.23.12 Linux x64, pinned by `r0/source-lock.json`. Main build job verifies original SHA and lock, runs `go test -c ./internal/pathmtu` **once**, exports the unchanged compiled binary and SHA256/provenance manifest. Separate consume job verifies same GitHub run+main SOURCE, original SHA, toolchain, package, lock SHA and binary SHA; executes **all** compiled native Go pathmtu tests once (`-test.v -test.count=1`) and requires the seven named original budget tests. Each job executes one package, no synthetic comparison, no cross-VM CPU ratio.

**done_when:** exact main SOURCE Actions build+consume SUCCESS, result artifact holds hash/run/native Go PASS, and M0 evidence receipt + cursor-only H checked against remote main. If failure, preserve failure reason and mark partial, never rename it PASS.

**Never inferred:** this only proves original pinned Go `pathmtu` compiled and its own tests ran. M3 Rust `FrameBudget` has separate SOURCE/run; **not** a combined qualification. Real Rust AEAD+8B HP, Normal/FEC-off seal→wire→authenticated open→business delivery, Go production V4, OS driver/physical and performance all remain NOT_RUN or NOT_IMPLEMENTED as applicable.

**Next one action after this atom:** M0 review/version-pin the exact Rust AEAD+8B HP dependencies needed by M3; M3 owns actual cipher implementation. After M3 true crypto S/H, coordinate real M1/M3/M4 same-SOURCE in-process packet integration, not mocks.
