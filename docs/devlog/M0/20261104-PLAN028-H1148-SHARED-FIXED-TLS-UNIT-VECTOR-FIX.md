# PLAN028 H1148 — correct strict shared fixed protected TLS test vector

H1147 [Action41835573934](https://github.com/lly8666/wbd-next/actions/runs/41835573934) failed at its original Go TLS unit before any actual native network test. New byte22/profile/three-cipher unit PASS; old H1144 shared-Normal feature unit erroneously sent fixed feature7 without the newly mandatory protected fixed profile+1, producing client ErrAdmissionParams and server ErrAdmissionUnsupported. Correct only original test helper shared+fixed positive vector to supply profile2 (default fixed profile1), while negative missing-profile still rejects. No fallback to guessed server setting or algorithm change. Exact manifest blob updated and one same ARM64+ARM64 real 70-UDP/Stop Action reissued; do not pretend H1147 already passed.

```feature-impact
{"kind":"none","ids":[],"reason":"Correct one protected TLS helper positive vector for the newly strict shared fixed-mode profile contract; product feature unchanged."}
```
