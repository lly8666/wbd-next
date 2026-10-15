# M0 approved policy mechanism for third M3 checker refresh

M3 worker task015 HEAD `79535dd5f57af0b5ec85ea812456ae0a31a3a4d2` has 100 immutable G2 activation commits. Main fixed paginated FULL-history audit at `529af37f`, run38711866188 SUCCESS, but worker-local old checker `817934b...` still rejects 100 commits. Never edit worker branch as M0.

One exceptional worker-owned root sync is authorized by main: direct first parent exactly `79535dd5...`, exactly one path `tools/worker_scope_ci.py`, one parent, copy **byte-identical** checker from separately approved **immutable M0 main source** and its Git blob as listed in `.governance/exceptions/M3-G2-015-checker.json`. This main-owned decision is published AFTER the checker source commit, avoiding self-hash/retroactive current-main mismatch; the checker verifies decision schema, exact parent, path, immutable reviewed source is ancestor of main and all source/worker blobs identical. It is not permission to edit any other tools or root file, merge main or reset history.

The M3 worker must perform its own one-file checker mirror from main as a new commit and rerun source exact worker Governance; M0 does not write to worker branch. Read-only M0 G2 audit independently verifies all source commits first. Task015 Release test remains separate from product/physical/500Mbps; old014 CPU ratios invalid.
