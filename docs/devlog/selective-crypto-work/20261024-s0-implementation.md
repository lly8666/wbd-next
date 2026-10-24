# 2026-10-24 S0 implementation and Actions intent

Remote verification at start: branch b94098c342552113ca136a178768f7f58bc433fd; main d8ba2cf270ff6ca5cadae6dab778c49c32636ef6 (behind 0). No experimental Actions runs or open requests existed at start. No available local checkout, and the public Git remote could not be resolved from the container, so local git status could not be substantiated; remote GitHub refs/files were checked. Source was reviewed from the experimental branch, not old conversation.

S0 source: commits a3354baf (isolated record), cb3b770d (feature), 0646535 (lib gate), d2a967b5 (paired tool), 98e5b09b972196b97476b4311346cb79681773c5 (ARM64 workflow). Feature is opt-in and absent from production callers; neither Go authentication/bootstrap negotiation nor real TUN driver is wired. This is an unverified component implementation, not a security/MTU/generation/Stop product receipt.

Action: native ARM64 S0 run 40108785993 attempt 1 job 120915933711 from exact SOURCE 98e5b09b972196b97476b4311346cb79681773c5. Initial observation: in_progress during source compilation/test step. Artifact and result are PENDING; no CPU measurement or pcap exists yet. In-code repeated-ciphertext fixture is a synthetic distinct-PN counterexample; it must not be called an actual kernel capture or actual TLS proof. S1 cost tool expects true TLS ciphertext record bytes prepared by Actions.

Known to inspect after S0: correctness of entire-record authentication, seal/open, size and feature defaults; invalid authenticated selective inner structure must never reach product delivery. Do not count untrusted pre-auth descriptor as authorization. No inherited network/FEC next_action executed; no main/peer status modified.
