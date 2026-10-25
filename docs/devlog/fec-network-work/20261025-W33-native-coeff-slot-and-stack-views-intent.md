# W33: bounded ISA-L coefficient refs & stack borrowed source/output arrays

W32 frozen W31 250Mbps double FAIL residual2.740/2.550%, Parity deficit8.61/8.57% with expired5610/5587 jobs and injector UDP send errors39/245, CPU PSI mean47.19 peak50.66. Clearly no claim all loss due to FEC. RX memory pressure, FEC seal and outer DATA retransmission = 0. User requested optimize after this single higher load.

In Rust FEC codec `PreparedBlock` allocates one BTreeMap entry per native row quantum even though coefficients already exist in global immutable SHARED_ENCODE_TABLES (k,row,count). Replace with fixed <=80 Option shared refs indexed by verified (first_row,count), preserve unique k from original global index. Existing native oracle across two blocks confirms pointer-equal immutable table sharing; change test access to bounded slot, keep same tests for exact math and backend.

In hot encode_prepared_into, replace the per-quantum allocations of Vec<&[u8]> and Vec<&mut [u8]> with stack arrays of exactly the existing limits MAX_K=16, MAX_BATCH_ROWS=4, and pass only occupied prefixes into same native Tables::encode. No unsafe; 10ms TTL, 32 M4 entries, source-first, original AEAD/PN and M4 definite-prefix unchanged. This removes five coefficient-reference tree nodes and 10 view Vecs per full k16/r20 block; no claim CPU win before measurement. Bounded extra PreparedBlock inline 80 pointer slot memory (~640 bytes per in-flight job), bounded count one per direction.

First build authentic native ARM64 product and complete Fixed/Auto missing-source TUN regression plus Maximum20 native contract. Then strict single-VM 250Mbps sequential A=W31 frozen B=W33 frozen, outer DATA retrans off, original fq600 and netem600Mbps/30%IID/300ms unchanged; record injector errors separately and result qualification, no 275+ load. No main/network branch edits.

## W34 verified result
## W34 2026-10-25: true 250Mbps sameVM old/new both PASS, host CPU variance explains earlier W32 failure

W33 source e99a4afff3e9e55e3a11113ed30097e1789e86af (fix of compile-only E0502 failed source ac4d9b21), native ARM64 build Action40147815858 real Fixed/Auto missing-source to TUN PASS artifact12580544395 SHA256 e1ec27312a833e03762a4b9bc6201ff143867b65a6dba02ce17a12a8bb9221eb; Maximum native row contract40147815849 PASS. Codec still exact global ISA-L (k,row,count), instead of per-quantum two heap-allocated pointer Vecs and per-block five BTreeMap coefficient reference entries uses fixed MAX_K16/MAX_BATCH_ROWS4 borrowed stack arrays and bounded 80-slot coefficient pointer array per in-flight block. No different mathematical output or FEC policy/M4 settlement.

[W34 A/B Action40148014701](https://github.com/lly8666/wbd-next/actions/runs/40148014701) **SUCCESS** single 4CPU ARM64 VM sequential A=W31 source3b16e796/B=W33 sourcee99a4aff, exact 250Mbps each, 30%IID netem/300ms one-way, outer netem600Mbps, unchanged original fq600 and owned static neighbors, original outer DATA retransmission truly0, authentic M2, warmup15 measure30 drain30. Artifact12581460257 SHA256 b64b94cebf5aa465421ee89bb310071401623820b9ed021630097fb92b5b785c.

| Metric | A old W31 | B new W33 |

|---|---:|---:|

| C2S delivered / residual |249.950Mbps / 0.02869%|249.936Mbps / 0.03631%|

| S2C delivered / residual |249.947Mbps / 0.03100%|249.950Mbps / 0.03127%|

| first-arrival p99 C2S/S2C |301.9/301.9ms|301.9/301.9ms|

| Parity planned/sent client |1382007/1381992|1381912/1381912|

| Parity planned/sent server |1381927/1381927|1381924/1381924|

| native parity jobs expired client/server |1/0|0/0|

| injector UDP send errors C2S/S2C |0/0|0/0|

| process CPU seconds/30 client/server |27.76/27.86|27.73/27.68|

| host CPU PSI mean/peak |33.66% / 36.11%|33.48% / 35.90%|

Both A/B true business/FEC-only scoped PASS and all native Fixed applied/zero source TUN and original root qdisc drops/zero RX pressure and codec reject, real recovered-to-TUN and Stop cleaned. **No causal W33 throughput gain:** observed combined CPU -0.21 seconds over30 (-0.38%); both parity complete and very similar p99/delivery; residual slightly higher B C2S. One AB cannot prove stable CPU saving.

**Cross-VM counterexample:** W32 on other shared Actions host, exactly same W31 old source3b16e796 at same250Mbps 30%/300ms, FAIL residual2.740/2.550%, real injector SndbufErrors39/245, native parity deficit8.61/8.57% and expired5610/5587; mean/peak CPU PSI47.19/50.66 versus W34 old A33.66/36.11. Host scheduling contention/CPU headroom and injector capacity are proven major sensitivities, no single-core IRQ saturation or cgroup throttling; cannot declare stable product250Mbps under high CPU pressure. Stop >250, no claimed host-fixed capacity, merge_ready=false. Further work should measure original TX M4 slot scheduling and high-PSI deadline age rather than chase ISA-L tables or enlarge RX buffers.
