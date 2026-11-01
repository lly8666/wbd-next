# H788 — H787 Windows route test never started due malformed workflow YAML

H787 exact-source code commit [4235bd31](https://github.com/lly8666/wbd-next/commit/4235bd31c78751c00f62e6efefe2e9d95f2bac04) adds private confirmed-only route-stage recovery algorithm and fake-backed unit. Its intended targeted [Action41309922227](https://github.com/lly8666/wbd-next/actions/runs/41309922227) **FAIL/INVALID WORKFLOW with zero jobs**. The test YAML was corrupted while constructing a string replacement containing literal `$'` from end-anchored Go test regex; JavaScript interpreted it as replacement suffix. This is workflow formatting, not product source/Go test FAIL.

H788 restores the previously syntactically valid workflow H786 content, then applies a literal callback replacement to preserve exact `-run '^TestN4(WindowsPersistedFullRouteReceiptsRejectMismatchWithoutOSWrites|OriginalConfirmedFullRouteCrashReplayFakeBackend)$'` and runs only that short Windows original Go test suite. Keeps frozen original donor manifest, Go recovery source, route permissions and safety gates unchanged. Explicit workflow FAIL and no-job status retained. H782 original Windows runner/first fault/GH API/ZIP and H786 read-only receipt test PASS remain distinct from H787 UNTESTED route-stage algorithm and genuine Game2FEC/WFP/DNS/Stop UNKNOWN.

```feature-impact
{"kind":"none","ids":[],"reason":"Fix only malformed scoped Windows Actions workflow test regex; production data plane and original Go recovery code unchanged."}
```
