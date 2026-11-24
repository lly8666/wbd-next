#!/usr/bin/env bash
# CI-only host TAP admission for original Android FakeTCP; manual workflow.
# Never modifies default route, firewall, netd, DNS or any production WBD.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
test "$(git rev-parse HEAD)" = "$GITHUB_SHA"
out=out/android-x86-tap-admission
mkdir -p "$out"
tap=wbdtapci0
phase=PREFLIGHT
created=0
tap_support=NOT_PROVEN
kernel_tap=NOT_PROVEN
host_ip=NOT_PROVEN
kvm=NOT_PROVEN
receipt(){
  local rc=$1
  WBD_TAP_PHASE="$phase" WBD_TAP_RC="$rc" \
  WBD_TAP_SUPPORT="$tap_support" WBD_TAP_KERNEL="$kernel_tap" \
  WBD_TAP_ADDRESS="$host_ip" WBD_TAP_KVM="$kvm" \
  python3 - <<'PY'
import json,os,pathlib
p=pathlib.Path("out/android-x86-tap-admission")
d={"schema":"wbd-android16-x86-kvm-tap-host-admission/v1",
 "source":os.environ["GITHUB_SHA"],
 "phase":os.environ["WBD_TAP_PHASE"],
 "exit_code":int(os.environ["WBD_TAP_RC"]),
 "host_arch":"x86_64",
 "host_kvm":os.environ["WBD_TAP_KVM"],
 "emulator_net_tap_help_advertised":os.environ["WBD_TAP_SUPPORT"],
 "kernel_tap_interface_create_readback":os.environ["WBD_TAP_KERNEL"],
 "isolated_host_tap_ipv4_readback":os.environ["WBD_TAP_ADDRESS"],
 "host_default_route_changed":False,
 "host_firewall_or_dns_changed":False,
 "guest_actual_tap_network":"NOT_RUN",
 "guest_exact_physical_network":"NOT_RUN",
 "original_go_faketcp_tls_m4":"NOT_RUN",
 "system_dns_takeover":"NOT_RUN"}
(p/"receipt.json").write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
print("D2_TAP_HOST_ADMISSION",d["emulator_net_tap_help_advertised"],
      d["kernel_tap_interface_create_readback"],d["isolated_host_tap_ipv4_readback"])
PY
}
cleanup(){
  local rc=$?
  trap - EXIT
  if [[ "$created" == 1 ]];then
    sudo -n ip link del "$tap" >/dev/null 2>&1 || true
  fi
  receipt "$rc" || true
  exit "$rc"
}
trap cleanup EXIT
test "$(uname -m)" = x86_64
# Reuse the exact proven Android16 KernelSU KVM permission admission.
# A fresh GitHub runner exposes /dev/kvm but not with user write permission
# until this workflow explicitly grants the ephemeral runner access.
if [[ ! -c /dev/kvm ]];then
 phase=ENV_BLOCKED_KVM_DEVICE
 exit 11
fi
if ! sudo -n chmod a+rw /dev/kvm;then
 phase=ENV_BLOCKED_KVM_PERMISSION_GRANT
 exit 11
fi
if [[ -r /dev/kvm && -w /dev/kvm ]];then
 kvm=PASS
else
 phase=ENV_BLOCKED_KVM_ACCESS
 exit 11
fi
test -c /dev/net/tun || { phase=ENV_BLOCKED_DEV_NET_TUN;exit 12; }
command -v ip >/dev/null || { phase=ENV_BLOCKED_IPROUTE2;exit 13; }
command -v sudo >/dev/null || { phase=ENV_BLOCKED_SUDO;exit 14; }
# A fresh hosted Ubuntu runner can have cmdline-tools but not yet the
# emulator package. The proven KSU job installs an Android system image
# (which pulls the emulator); this host-only admission installs ONLY the
# emulator binary, not an AVD, manager, phone image or guest network.
if [[ -z "$ANDROID_HOME" ]];then
 phase=ENV_BLOCKED_SDK_HOME
 exit 15
fi
if [[ ! -x "$ANDROID_HOME/emulator/emulator" ]];then
  sdkmanager="$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager"
  if [[ ! -x "$sdkmanager" ]];then
    phase=ENV_BLOCKED_SDKMANAGER
    exit 15
  fi
  if ! printf 'y\n' | "$sdkmanager" "emulator" >"$out/emulator-install-private.txt" 2>&1;then
    phase=ENV_BLOCKED_EMULATOR_INSTALL
    exit 15
  fi
  rm -f "$out/emulator-install-private.txt"
fi
if [[ ! -x "$ANDROID_HOME/emulator/emulator" ]];then
  phase=ENV_BLOCKED_EMULATOR_BINARY
  exit 15
fi
# Advertised API support only, NOT a proven guest TAP boot.
if timeout 20s "$ANDROID_HOME/emulator/emulator" -help-net-tap >"$out/tap-help-private.txt" 2>&1 &&
   grep -Fq -- '-net-tap' "$out/tap-help-private.txt";then
  tap_support=ADVERTISED_NOT_GUEST_VERIFIED
else
  phase=ENV_BLOCKED_EMULATOR_NET_TAP_FLAG
  exit 16
fi
rm -f "$out/tap-help-private.txt"
if ip link show dev "$tap" >/dev/null 2>&1;then
  phase=REFUSE_PREEXISTING_TAP
  exit 17
fi
# A single isolated device owned by this workflow; no host route or NAT.
sudo -n ip tuntap add dev "$tap" mode tap user "$(id -un)"
created=1
if sudo -n ip link show dev "$tap" >/dev/null 2>&1;then
  kernel_tap=PASS
else
  phase=ENV_BLOCKED_TAP_CREATE_READBACK
  exit 18
fi
sudo -n ip addr add 10.254.63.1/24 dev "$tap"
sudo -n ip link set dev "$tap" up
if ip -o -4 addr show dev "$tap" | grep -Fq '10.254.63.1/24';then
  host_ip=PASS
else
  phase=ENV_BLOCKED_TAP_ADDR_READBACK
  exit 19
fi
phase=TAP_HOST_READY_FOR_SEPARATE_GUEST_PILOT
echo D2_TAP_KERNEL_INTERFACE_WITH_ISOLATED_IPV4_READBACK_PASS
