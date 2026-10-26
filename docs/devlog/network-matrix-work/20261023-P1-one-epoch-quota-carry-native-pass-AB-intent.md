# 2026-10-23 P1 one-epoch unused quota credit native PASS → one same-VM AB

Native Action39900920663 SOURCE `a05e059600d6970a91d5d8f9e6fd3851e6745233` SUCCESS. Product artifact12478957278 SHA256 `47115e0e874a3fca25bef9fa430d6760c1d5c28ed60cfb3ed66dab4e23e41c0a`; MTU artifact12479295557 SHA256 `7782214f2e349d41a14f71755abd2ca33923fa97a558b7a771ba8892d4aa1bc2`.

Pure carry invariant PASS: epoch0 uses12,000B of32,768B, exactly20,768B unused becomes epoch1 credit; epoch1 effective53,536B admits52,500B and rejects another1500B; after consuming carry, epoch2 returns exactly32,768B. No second-generation accumulation. First-repair priority, adaptive RTT, retirement diagnostics, exact block reason classifier, Fixed M2 and9 MTU/DF/Stop also PASS.

One same-VM AB follows: A=6746 first-priority/no-carry, B=a05e one-epoch carry. Same exact Normal2%/200ms/60s request. Long-run repair rate, retry count, pacer, PTO/cache, auth/crypto, traffic and seed are unchanged.
