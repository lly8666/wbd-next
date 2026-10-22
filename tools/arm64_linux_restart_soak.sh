#!/usr/bin/env bash
# Exactly two real original Go TLS ↔ Rust ARM64 kernel/TUN sessions,
# complete Stop+namespace teardown and *new* certificate/credentials.
# Not a physical-host qualification or a packet-level source-loss witness.
set -euo pipefail
test "$(uname -m)" = aarch64
: "${GITHUB_SHA:?}" "${GITHUB_RUN_ID:?}" "${GITHUB_WORKSPACE:?}"
root="$GITHUB_WORKSPACE"
output="$root/arm64-restart-result"
mkdir -p "$output"
# Use an exact binary/source frozen in the workflow, NOT a harness SHA.
test -n "${WBD_ARM64_FROZEN_SOURCE:?}"
for iteration in 1 2; do
  if [ "$iteration" -eq 1 ]; then
    export WBD_ARM64_IDLE_RESUME_S=8
  else
    unset WBD_ARM64_IDLE_RESUME_S
  fi
  echo "ARM64_RESTART_EPISODE_BEGIN $iteration"
  # Its trap destroys BOTH network namespaces on any early failure, and
  # its success receipt is written only after both Go native Stops.
  bash "$root/tools/arm64_linux_netns_smoke.sh"
  test -d "$root/arm64-netns-result"
  mv "$root/arm64-netns-result" "$output/episode-$iteration"
  ep="$output/episode-$iteration"
  test -s "$ep/tls-cert-fingerprint.txt"
  grep -q V4_PUBLIC_NATIVE_STOP_DRAINED "$ep/client.log"
  grep -q V4_PUBLIC_NATIVE_STOP_DRAINED "$ep/server.log"
  test ! -d "$RUNNER_TEMP/arm64-netns-secrets-$GITHUB_RUN_ID"
  # Stop must truly retire the original M4 interfaces. The namespace name is
  # deliberately REUSED in episode 2 to detect stale kernel resources.
  if sudo -n ip netns list | grep -Eq "wac$GITHUB_RUN_ID|was$GITHUB_RUN_ID"; then
    echo "ARM64_RESTART_NAMESPACE_LEAK episode=$iteration" >&2
    exit 1
  fi
  if [ "$iteration" -eq 1 ]; then
    grep -q 'ARM64' "$ep/receipt.json" || true
    test -s "$ep/idle-resume-c2s.log"
    test -s "$ep/idle-resume-s2c.log"
  fi
  echo "ARM64_RESTART_EPISODE_STOP_DRAINED $iteration"
done
OUTPUT="$output" python3 - <<'PY'
import json,os,pathlib,hashlib,re
p=pathlib.Path(os.environ["OUTPUT"])
docs=[]
for n in (1,2):
    d=p/f"episode-{n}"
    receipt=json.loads((d/"receipt.json").read_text())
    assert receipt["source"]==os.environ["WBD_ARM64_FROZEN_SOURCE"]
    assert receipt["mode"]=="fec-fixed"
    assert receipt["netns_cleanup"]=="PASS"
    assert receipt["owned_stop"]=="TWO_DRAINED"
    assert (d/"tls-cert-fingerprint.txt").read_text().strip()
    def ping(fn,expected):
        s=(d/fn).read_text()
        m=re.search(r'(\d+) packets transmitted,\s*(\d+) received',s)
        assert m and (int(m[1]),int(m[2]))==(expected,expected),(fn,s)
    ping("c2s.log",20);ping("s2c.log",20)
    if n==1:
        ping("idle-resume-c2s.log",4);ping("idle-resume-s2c.log",4)
    for role in ("client","server"):
        log=(d/f"{role}.log").read_text()
        assert log.count("V4_ORIGINAL_GO_"+role.upper()+"_NATIVE_READY")==1
        assert "V4_PUBLIC_NATIVE_STOP_DRAINED" in log
        assert re.search(r'V4_PUBLIC_FEC2_READBACK role='+role+
             r' mode=fixed requested=\d+ applied=[1-9]\d* .*pending=false',log)
    docs.append({"episode":n,"mode":"fec-fixed",
      "certificate_fingerprint_sha256":hashlib.sha256((d/"tls-cert-fingerprint.txt").read_bytes()).hexdigest(),
      "two_way_original_ICMP_20_of_20":True,
      "idle_8s_and_two_way_4_of_4":n==1,
      "Stop":receipt["owned_stop"],"namespace_cleanup":receipt["netns_cleanup"],
      "secret_directory":"DELETED"})
assert docs[0]["certificate_fingerprint_sha256"]!=docs[1]["certificate_fingerprint_sha256"],"TLS certificate was reused"
out={"qualification":"PASS_SCOPED_ARM64_TWO_SEQUENTIAL_REAL_GO_TLS_RUST_TUN_GENERATIONS",
     "binary_source":os.environ["WBD_ARM64_FROZEN_SOURCE"],
     "harness_source":os.environ["GITHUB_SHA"],
     "native_original_client_server":"TWO_DISTINCT_SESSIONS",
     "credential_rotation":"PUBLIC_TLS_CERT_FINGERPRINT_DIFFERS",
     "outer_kernel_fault":"NOT_RUN",
     "physical_two_hosts":"NOT_RUN",
     "long_duration_soak":"NOT_RUN",
     "episodes":docs}
(p/"receipt.json").write_text(json.dumps(out,indent=2)+"\n")
print("ARM64_ORIGINAL_GO_RUST_NATIVE_TWO_GENERATIONS_STOP_RECREATE_PASS")
PY
