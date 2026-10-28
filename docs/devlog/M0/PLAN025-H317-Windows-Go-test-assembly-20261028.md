# PLAN025 H317 — exact original-Go Windows preflight test assembly correction

H315/H316 Windows regression source included dedicated Go negative test files, but the pinned original-Go runtime was prepared via tools/prepare_windows_wiring.py EXTRA_BRIDGES, which did not yet include the new two realityfront tests. Calling a compiled Go test binary with -test.run can return success for zero matched tests; consequently the previous Windows Go compile PASS did NOT establish that either new M2/M3 table test ran. This is a test-harness coverage omission, not a Windows product PASS or product FAIL.

Add the two exact test files to shared original-Go assembly and add Python CI assertions that each intended test name and source path is source-present. Same original Go donor SHA; no Linux product code changes. Keep prior action outcomes and Windows Normal 240s request unchanged. Test presence now enforced before full 240s.

```feature-impact
{"kind":"none","ids":[],"reason":"Exact-source Windows assembly test coverage and regression guard only."}
```
