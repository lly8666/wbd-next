# H987 PLAN027A — repair cursor 8-ref bound; reuse original H986 native build

H986 `1e8325f16e2975a9da3497ab97ac570771a97238` started original signed Windows+WSL2 product compile Action [41546652567](https://github.com/lly8666/wbd-next/actions/runs/41546652567). Original H986 dispatcher [41546626999](https://github.com/lly8666/wbd-next/actions/runs/41546626999) passed source/fixture preflight. The governance Action [41546627869](https://github.com/lly8666/wbd-next/actions/runs/41546627869) failed `SCOPE_AUDIT_FAILED: unbounded context_refs`: ten history pointers exceed `.governance/policy.json` max eight. This is metadata FAIL, not a measured MTU/DF regression. No unknown test result is overwritten.

Trim M0 cursor to exactly eight most recent paired context refs. Reuse H986 binary SOURCE and run ID, checking source-exact Git diff excludes all crates/Go/Cargo/installers, both real Windows/Linux artifact names and successful build before dispatching each of DF0/DF1, Auto-staged, Game4FEC-staged in a separate Windows/WSL2 measurement Action. If original build fails, stop without re-dispatch. Changed workflow helper/harness/source ref H987 is not a new product binary. Scope remains PLAN027A and NOT_RUN until proven; no 1500 default or new recovery machinery.

```feature-impact
{"kind":"none","ids":[],"reason":"Only restore cursor bound and reuse an already running exact product source; no runtime, ABI or feature implementation changes."}
```
