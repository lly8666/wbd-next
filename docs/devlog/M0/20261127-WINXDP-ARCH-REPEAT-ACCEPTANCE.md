# M0 counterbalanced architecture candidate acceptance — 2026-11-27

Run45956003470, fixture 87492b559752659a03271df6d69d96c16a3c3bd5, exact DLL57b2168 from45951388258. Audit snapshot: 48 matrix jobs, 38 CPU skips, 9 real9V45 jobs/112 business cases, 28 quartets, 26 valid MATCHED_TARGET with mechanism exercised. One cipher TCP G job140362514170 stalled WSL stage3 from07:05:19Z, logs BlobNotFound; coverage aggregate has not run. Cipher UDP all12 CPU-skipped. No product change or release promotion.

## TX completion refill
TCP up350 ABBA/BAAB: F -9.60/-16.47%, G +2.46/-2.28%, E +3.66/+10.80%, A +5.54/+0.26%. Mixed, no stable general gain. Maximum UDP1200B5% RTT40 150+150: H -3.11/-10.07%, J -19.80/-10.57%, all four valid, near target. Earlier run45951388258 Maximum UDP -6.94/+5.41%, Maximum TCP1% duplex100 -0.23%; no broad mode-wide proof. Normal UDP288B100+100 J -5.17/-8.97%, H both invalid (rc1 in 3 legs, TUN tx drops6839/4150/31046, both A and B, exact owned Stop and XDP RX drop0); prior valid +5.38%. Retain candidate scoped to high-rate Fixed/Maximum as research hypothesis; no automatic FEC-specific default based on these samples alone. TX early refill exercised, zero credit-limited in observed cases; effect not proven to come from actual credit starvation.

## Immutable ciphertext copy outside owner lock
TCP up350 C +27.96/-18.19%, E -1.44/-4.01%, A +38.36/-1.54%; duplex175 C +5.78/-1.87%, E +0.76/-3.76%, A -4.40/+2.74%. Prior -15.57 upload and +1.44 duplex. Same-host order reversal demonstrates inconsistent benefit; no adoption. UDP untested due CPU gate, not a negative result. Avoid broad repeated trials unless discriminating lock/ownership mechanism evidence emerges. Candidate is not zero-copy. Retain source and structured receipts, prefer original frozen path.
 
## Scope
All observed cases had zero XDP RX drops and zero credit-limited; published and completed matched. CPU/GiB Windows process only, not kernel/system cost. No new test or product source change. Preserve freeze branch 6c8ba05. No cancellation or claim final workflow success. Raw structured case/pair receipts: docs/evidence/M0/WINXDP-ARCH-REPEAT-45956003470.json.
