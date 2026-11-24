#!/usr/bin/env bash
# Sourced by D2 after real KSU App grant, same-source assets, and one
# original host server. No benchmark or fake TLS.
set -euo pipefail
matrix="$out/wiring"
mkdir -p "$matrix"
: >"$matrix/results.tsv"
modes=(normal fec-fixed fec-auto game2 game2-fixed game4 game4-fixed)
failed=0
for mode in "${modes[@]}";do
  case_dir="$matrix/$mode"
  mkdir -p "$case_dir"
  adb push "$tmp/password" /data/local/tmp/wbd-d2-pass.tmp >"$case_dir/stage.txt" 2>&1
  adb push "$tmp/route.hex" /data/local/tmp/wbd-d2-route.tmp >>"$case_dir/stage.txt" 2>&1
  adb push "$tmp/server-cert.pem" /data/local/tmp/wbd-d2-ca.tmp >>"$case_dir/stage.txt" 2>&1
  adb shell su -c '/system/bin/sh /data/local/tmp/wbd-x86-ci/wbd-d2-cred-stage.sh' >"$case_dir/stage-result.txt" 2>&1
  grep -Fxq D2_CI_APP_PRIVATE_SECRET_STAGING_PASS "$case_dir/stage-result.txt"
  adb shell logcat -c >/dev/null
  activity_requested=1
  adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity \
    --es ci_step start --es ci_mode "$mode" >"$case_dir/start.txt" 2>&1
  reached=NOT_PROVEN
  for _ in $(seq 1 16);do
    adb shell logcat -d -s WBD_ROOT_DIAG:I WBD_X86_CI_ORIGINAL:I '*:S' >"$case_dir/diagnostics.txt"
    if grep -Fq ORIGINAL_GO_MODE_READBACK_MATCHED "$case_dir/diagnostics.txt" &&
       grep -Fq ORIGINAL_GO_TUN_KERNEL_CONFIGURED "$case_dir/diagnostics.txt" &&
       grep -Fq ORIGINAL_GO_RAW_SOCKET_READY "$case_dir/diagnostics.txt" &&
       grep -Fq ORIGINAL_GO_COLD_SYN_TX_OK "$case_dir/diagnostics.txt";then
      reached=PASS
      break
    fi
    if grep -Eq 'START_REFUSED|ROOT_PROCESS_EXIT_|ROOT_LAUNCH_FAILED|ORIGINAL_ROOT_SERVICE_CI_START_BLOCKED' "$case_dir/diagnostics.txt";then break;fi
    sleep 0.5
  done
  adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity \
    --es ci_step stop >"$case_dir/stop.txt" 2>&1
  cleaned=NOT_PROVEN
  for _ in $(seq 1 20);do
    adb shell logcat -d -s WBD_ROOT_DIAG:I WBD_X86_CI_ORIGINAL:I '*:S' >"$case_dir/diagnostics.txt"
    if grep -Fq OWNER_CLEANUP_FINISHED "$case_dir/diagnostics.txt" &&
       adb shell su -c 'test ! -e /sys/class/net/wbdv40 && test ! -e /data/local/tmp/wbd-next-root/rst-guard.json' >/dev/null 2>&1;then
      if rules="$(adb shell su -c 'iptables -S OUTPUT' 2>/dev/null)" &&
         ! grep -Fq wbd-next-root-rst-v1 <<<"$rules";then
        cleaned=PASS
        break
      fi
    fi
    sleep 0.5
  done
  printf '%s\t%s\t%s\n' "$mode" "$reached" "$cleaned" >>"$matrix/results.tsv"
  cp "$case_dir/diagnostics.txt" "$out/app-diagnostic-enums.txt"
  echo "ANDROID_WIRING_MODE_RESULT $mode preauth=$reached cleanup=$cleaned"
  if [[ "$reached" != PASS || "$cleaned" != PASS ]];then failed=1;fi
  # Do not hide an uncertain owner with another START.
  if [[ "$cleaned" != PASS ]];then break;fi
  activity_requested=0
  sleep 1
done
python3 - "$matrix" <<'PY'
import json,os,pathlib,sys
p=pathlib.Path(sys.argv[1])
rows={}
for line in (p/"results.tsv").read_text().splitlines():
    mode,preauth,cleanup=line.split("\t")
    rows[mode]={"preauth":preauth,"preauth_cleanup":cleanup,
                "full_group_tls_lease_m4_business":"NOT_PROVEN"}
for mode in ("normal","fec-fixed","fec-auto","game2","game2-fixed","game4","game4-fixed"):
    rows.setdefault(mode,{"preauth":"NOT_RUN","preauth_cleanup":"NOT_RUN",
                          "full_group_tls_lease_m4_business":"NOT_RUN"})
(p/"receipt.json").write_text(json.dumps({"source":os.environ["GITHUB_SHA"],"scope":"production RootService + real Bionic Go parse/TUN/first RAW/SYN and owned preauth cleanup; not peer TLS or all Game lanes","modes":rows},indent=2)+"\n")
PY
# Actual Bionic Go TLS/admission test binary. Real TLS with the
# original association harness, not live physical M4 traffic.
tls_status=NOT_RUN
if [[ -s "$n/wiring-bionic-tls-amd64.test" ]] &&
   grep -Fxq PASS "$n/wiring-bionic-tls-build-status.txt";then
  adb push "$n/wiring-bionic-tls-amd64.test" /data/local/tmp/wbd-ci-tls.test >"$matrix/bionic-tls-stage.txt" 2>&1
  adb shell chmod 700 /data/local/tmp/wbd-ci-tls.test
  if timeout 150s "$ANDROID_HOME/platform-tools/adb" shell '/data/local/tmp/wbd-ci-tls.test -test.v -test.timeout=120s -test.run="^(TestPLAN028SharedNormalPerClientFECProtectedCapability|TestPLAN028MixedOne443OriginalProtectedNormalGame2Game4ColdPolicy|TestM0V4OriginalTLSGame2And4AuthenticatedColdSet|TestH2401GameColdAttemptTracksFreshLane1BeforeReply|TestFECGameProtectedV4ProfileWireOffAndFailClosed|TestA38OriginalProtectedAdmissionCertVerifyPolicy)$"' >"$matrix/bionic-tls.log" 2>&1;then
    tls_status=PASS
    for name in TestPLAN028SharedNormalPerClientFECProtectedCapability TestPLAN028MixedOne443OriginalProtectedNormalGame2Game4ColdPolicy TestM0V4OriginalTLSGame2And4AuthenticatedColdSet TestH2401GameColdAttemptTracksFreshLane1BeforeReply TestFECGameProtectedV4ProfileWireOffAndFailClosed TestA38OriginalProtectedAdmissionCertVerifyPolicy;do
      if ! grep -Fq -- "--- PASS: $name " "$matrix/bionic-tls.log";then tls_status=FAIL;fi
    done
  else tls_status=FAIL;fi
  adb shell rm -f /data/local/tmp/wbd-ci-tls.test
else
  tls_status=BUILD_FAIL
fi
printf '%s\n' "$tls_status" >"$matrix/bionic-tls-status.txt"
echo "ANDROID_WIRING_BIONIC_TLS $tls_status"
if [[ "$tls_status" != PASS ]];then failed=1;fi
test "$failed" = 0
