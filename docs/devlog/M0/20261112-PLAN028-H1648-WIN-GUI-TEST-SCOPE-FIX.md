# PLAN028 H1648 | WinForms compiled GUI source regression, C# test-only scope fix

Latest [H1647 GUI Windows2025 VM Action43160277750](https://github.com/lly8666/wbd-next/actions/runs/43160277750) **whole FAIL**; no original Go/Rust network test attempted in this Action. Frozen original Rust ISA-L DLL hash and exact new current Go V4 cold build/manifest assemble passed, then Roslyn refused `GuiTests.cs(93,...): CS0103 configForm does not exist`. H1647 added a second `foreach` after the original `using(var configForm=...) foreach(...)` single-statement scope, leaving the configuration editor outside the lexical `using` scope. This is **test-only C# scoping error before GUI button/config execution**, not proof that FEC native profile or Rust is broken. Keep original Action status FAIL.

H1648 changes only two exact GUI test fixture snippets in `r0/go_overlay/assembly/manifest-plan020-m0.json`: put both the hidden-carrier assertions and per-visible-field save/real CLI check into one explicit `using { ... }` lexical scope. All prior product choices unchanged: native FEC Off default, Fixed7 true Rust ratios (1/8..5/4) and Normal-only Auto; hidden Go cold carrier derived from FEC2 mode; 21 fixed grade × lane config cases and button visibility tests remain strict, not removed. Do not count as PASS before next independent VM terminal Action.

H1647 governance [Action43160277739](https://github.com/lly8666/wbd-next/actions/runs/43160277739) SUCCESS; automatically triggered x86/Windows/ARM library checks may run alongside GUI but this single test-only edit doesn't require repeating historical signed seven-mode weaknet. Independent Windows controller/DUT/Linux1800s unavailable, near-inner-MTU and same-Windows two Wintuns explicitly skipped; no 029/030.

```feature-impact
{"kind":"none","ids":[],"reason":"Only exact C# test fixture using-scope around hidden/visible FEC UI validation; no product source/default, Rust or protocol change."}
```
