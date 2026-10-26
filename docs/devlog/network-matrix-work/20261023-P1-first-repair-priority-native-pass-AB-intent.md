# 2026-10-23 P1 first-repair hard-quota priority native PASS → one same-VM AB

Native Action39899738046 SOURCE `6746e32e27a555cbcd250e980a1f1337d92f0b60` completed SUCCESS. Product artifact12477859860 SHA256 `114de9c9a3b7c074d527273009ce369eee2508202323619cbc06189c0b68be40`; MTU artifact12478243408 SHA256 `b42a82e60f7eb299a69e9f295cb9b1ab26030cb173d6dbb83ff33a08a94c2d4b`.

The failed 20ms product rearm is reverted. New native unit proves: retry-stage repairs can exhaust the8-MTU smoothing bucket and the next retry gets BurstPaced; a stage0 first repair still reserves under the unchanged hard epoch quota; when that priority reservation is definitely NotSent it refunds only the exact token debit (zero in the empty-bucket case), so no token credit is invented. Candidate stage originates in ReceiptState and preflight requires it still equal the entry's actual repair_attempts. Adaptive RTT, retirement diagnostics, exact block classifier, Fixed M2 and nine MTU/DF/Stop cases also PASS.

One causal AB follows: A=d9dc old first-repair-paced baseline, B=6746 first-repair hard-quota priority. Same VM, same exact Normal2%/200ms/60s request. No quota/burst size/PTO/cache/load/seed changes.
