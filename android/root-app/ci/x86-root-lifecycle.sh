#!/usr/bin/env bash
# Source only in the existing real D2 host/guest fixture. Preauth lifecycle,
# no claim of READY automatic recovery or saved-profile handover.
set -euo pipefail
d="$out/lifecycle"
mkdir -p "$d"
: >"$d/results.tsv"
failed=0
record(){ printf '%s\t%s\n' "$1" "$2" >>"$d/results.tsv";echo "B92_LIFECYCLE $1 $2";[[ "$2" == PASS ]] || failed=1; }
log(){ adb shell logcat -d -s WBD_ROOT_DIAG:I WBD_X86_CI_ORIGINAL:I '*:S' >"$d/$1.log"; }
start_case(){
 local label="$1" mode="$2"
 adb push "$tmp/password" /data/local/tmp/wbd-d2-pass.tmp >"$d/$label-stage.txt" 2>&1
 adb push "$tmp/route.hex" /data/local/tmp/wbd-d2-route.tmp >>"$d/$label-stage.txt" 2>&1
 adb push "$tmp/server-cert.pem" /data/local/tmp/wbd-d2-ca.tmp >>"$d/$label-stage.txt" 2>&1
 adb shell su -c '/system/bin/sh /data/local/tmp/wbd-x86-ci/wbd-d2-cred-stage.sh' >"$d/$label-stage-result.txt" 2>&1
 grep -Fxq D2_CI_APP_PRIVATE_SECRET_STAGING_PASS "$d/$label-stage-result.txt" || return 1
 adb shell logcat -c
 activity_requested=1
 adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity --es ci_step start --es ci_mode "$mode" >"$d/$label-start.txt"
 for _ in $(seq 1 20);do
  log "$label"
  if grep -Fq ORIGINAL_GO_MODE_READBACK_MATCHED "$d/$label.log" &&
     grep -Fq ORIGINAL_GO_TUN_KERNEL_CONFIGURED "$d/$label.log" &&
     grep -Fq ORIGINAL_GO_RAW_SOCKET_READY "$d/$label.log" &&
     grep -Fq ORIGINAL_GO_COLD_SYN_TX_OK "$d/$label.log";then return 0;fi
  if grep -Eq 'START_REFUSED|ROOT_PROCESS_EXIT_|ROOT_LAUNCH_FAILED|ORIGINAL_ROOT_SERVICE_CI_START_BLOCKED' "$d/$label.log";then return 1;fi
  sleep .25
 done
 return 1
}
state(){
 adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity --es ci_step lifecycle_state >/dev/null
 sleep .2
 adb shell logcat -d -s WBD_X86_CI_ORIGINAL:I '*:S' | tr -d '\r' | grep B92_LIFECYCLE_STATE | tail -1
}
cleaned(){
 local label="$1"
 for _ in $(seq 1 32);do
  log "$label"
  if grep -Fq OWNER_CLEANUP_FINISHED "$d/$label.log" &&
     adb shell "su -c 'test ! -e /sys/class/net/wbdv40 && test ! -e /data/local/tmp/wbd-next-root/rst-guard.json'" >/dev/null 2>&1;then
   local rules
   if rules="$(adb shell su -c 'iptables -S OUTPUT')" && ! grep -Fq wbd-next-root-rst-v1 <<<"$rules";then
    activity_requested=0
    return 0
   fi
  fi
  sleep .25
 done
 return 1
}
stop_case(){
 adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity --es ci_step stop >"$d/$1-stop.txt"
 cleaned "$1"
}
write_receipt(){
 python3 - "$d" <<'PY'
import json,os,pathlib,sys
p=pathlib.Path(sys.argv[1])
r={"source":os.environ["GITHUB_SHA"],"scope":"production RootService preauth lifecycle, physical Network change and explicit restart; not READY automatic recovery/profile transition","scenes":dict(line.split("\t") for line in (p/"results.tsv").read_text().splitlines()),"ready_automatic_recovery":"NOT_PROVEN","ready_profile_switch":"NOT_PROVEN"}
(p/"receipt.json").write_text(json.dumps(r,indent=2)+"\n")
print(json.dumps(r))
PY
}
if start_case background normal;then
 before="$(adb shell su -c 'cat /data/local/tmp/wbd-next-root/owner.pid' 2>/dev/null || true)"
 adb shell input keyevent KEYCODE_HOME
 sleep .5
 adb shell dumpsys activity services org.wbdnext.rootclient >"$d/background-service.txt"
 adb shell am start -n org.wbdnext.rootclient/.RootClientActivity >"$d/foreground-activity.txt"
 after="$(adb shell su -c 'cat /data/local/tmp/wbd-next-root/owner.pid' 2>/dev/null || true)"
 # Do not log the owner token. Equality only.
 if [[ -n "$before" && "$before" == "$after" ]] &&
    grep -Fq RootClientService "$d/background-service.txt" &&
    state | grep -Fq 'active=true';then record background-foreground PASS
 else record background-foreground FAIL;fi
else record background-foreground FAIL;fi
if stop_case background;then record explicit-stop PASS;else record explicit-stop FAIL;write_receipt;exit 1;fi
if start_case reconfigure fec-fixed;then record cold-mode-restart PASS;else record cold-mode-restart FAIL;fi
selected="$(grep -E 'CI_SELECTED_PHYSICAL_IFACE_(WLAN0|ETH0|OTHER)' "$d/reconfigure.log" | tail -1 || true)"
loss=NOT_PROVEN
case "$selected" in
 *WLAN0*)
  # Disposable guest only. Restore Wi-Fi even after an unproven callback.
  adb shell svc wifi disable
  for _ in $(seq 1 20);do
   log network-loss
   if grep -Fq STOP_REQUESTED "$d/network-loss.log";then
    if cleaned network-loss;then loss=PASS;fi
    break
   fi
   sleep .25
  done
  adb shell svc wifi enable
  ;;
 *) loss=ENV_BLOCKED ;;
esac
record network-loss-preauth "$loss"
if [[ "$loss" != PASS ]];then
 if ! stop_case reconfigure;then record fallback-explicit-stop FAIL;write_receipt;exit 1;fi
fi
if [[ "$loss" == PASS ]];then
 recovered=0
 for _ in $(seq 1 24);do
  adb shell am start -n org.wbdnext.rootclient/.X86CiOriginalStartActivity --es ci_step specialty_scope >/dev/null
  sleep .5
  log recovery
  if grep -Eq 'B90_SCOPE [0-9]+ wlan0 ' "$d/recovery.log";then recovered=1;break;fi
 done
 if [[ "$recovered" == 1 ]] && start_case restored normal;then
  record restored-network-manual-start PASS
  if stop_case restored;then record restored-stop PASS;else record restored-stop FAIL;fi
 else record restored-network-manual-start FAIL;fi
else record restored-network-manual-start NOT_RUN;fi
write_receipt
test "$failed" = 0
