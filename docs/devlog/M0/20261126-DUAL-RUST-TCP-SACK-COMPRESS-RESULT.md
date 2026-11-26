# M0 SACK compression result

docs/evidence/M0/20261126-DUAL-RUST-TCP-SACK-COMPRESS-RESULT.json

Run45842115562 12/12 measured + matching probes + joined Stop; native45842035087 both ISA success, core45842115480 332 pass. Three ZIP hashes matched, 1727 sampled direct paths, actual qdisc loss checked, bare782.8Mbps below absolute qualification. A/B same source, same profile within block, cap64 at 0%, loss10 at 1/5%. Throughput 256.13→315.93, 60.76→61.32, 16.72→15.09 Mbps. Client ACK/DATA pooled 69.95→11.05%, 99.70→6.74%, 99.84→26.26%. CPU/GiB both endpoints and relay inclusive improved, but 5% throughput lower with high baseline variance. Keep diagnostic candidate, not promote default or retire splice; investigate zero-injection retransmissions and loss feedback/recovery, separate GRO. No further product edits or repeated dispatch.
