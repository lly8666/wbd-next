#!/usr/bin/env bash
# B2c1 REAL Linux kernel loopback UDP/TCP socket qualification for the
# Android physical-netd binder's platform-independent Go safety contract.
# The actual NDK android_setsocknetwork is compiled into ARM64 ELF in
# arm64-native; it cannot be EXECUTED here without Android16 ARM64 KVM.
set -euo pipefail
cd "${GITHUB_WORKSPACE:?Actions checkout required}"
test "$(git rev-parse HEAD)" = "${GITHUB_SHA:?SOURCE required}"
mkdir -p out/android-b2c-physical
export GO111MODULE=off GOTOOLCHAIN=local
go test -count=1 -timeout=35s -v \
  -run '^TestB2cPhysical' \
  ./r0/go_overlay/internal/v4productcli/dnsnative \
  | tee out/android-b2c-physical/go-physical-real-loopback.log
for test in \
 TestB2cPhysicalScopeRealUDPAndTruncatedSameScopedTCP \
 TestB2cPhysicalScopeRejectsTunnelEndpointAndUnboundCallback \
 TestB2cPhysicalSocketBindFailureNeverSendsAndNeverFallsBack \
 TestB2cPhysicalScopeMustMatchOriginalKernelInterfaceIPv4AndMTU;do
 grep -Fq -- "--- PASS: $test" out/android-b2c-physical/go-physical-real-loopback.log
done
python3 - <<'PY'
from pathlib import Path
import hashlib,json,os
root=Path("r0/go_overlay/internal/v4productcli")
source=(root/"dnsnative/physical_android_cgo.go").read_text()
common=(root/"dnsnative/physical.go").read_text()
go=(root/"linux.go").read_text()
assert "#include <android/multinetwork.h>" in source
assert "C.android_setsocknetwork" in source and "SO_BINDTODEVICE" in source
assert "wbd_dns_socket_device_matches" in source and "getsockopt(" in source
assert "#include <net/if.h>" in source and "IFNAMSIZ" in source
assert "strcmp(actual,expected)==0?1:0" in source and "ErrUnbound" in source
assert "d.ControlContext=" in common and "d.LocalAddr=" in common
assert 'network4:=network+"4"' in common
assert "dnsnative.NewAndroidPhysicalDNSDialer(" in go
assert "V4_PUBLIC_ANDROID_PHYSICAL_DNS_COLD_SCOPE_CHECKED" in go
out=Path("out/android-b2c-physical")
receipt={
 "schema":"wbd-android-b2c1-physical-dns-scoped-dialer/v1",
 "source":os.environ["GITHUB_SHA"],
 "android_cgo_binder_sha256":hashlib.sha256(source.encode()).hexdigest(),
 "real_host_lo_udp_and_tc_tcp_dns":"PASS",
 "real_host_fd_ControlContext_invocation":"PASS",
 "real_host_bind_failure_no_udp_send":"PASS",
 "rejected_tunnel_wrong_endpoint_and_bad_ifindex_mtu_ip":"PASS",
 "android_setsocknetwork_bionic":"CROSS_COMPILE_ONLY_NOT_EXECUTED",
 "dns_server_production":"223.5.5.5:53_PHYSICAL_ONLY",
 "android_real_physical_dns_socket":"NOT_RUN",
 "wbd_rust_tun_dns_packet_capture":"NOT_CONNECTED",
 "android_system_resolver":"NOT_CONNECTED",
 "kvm_android16_p2_p3":"ENV_BLOCKED",
 "physical_ksu":"NOT_RUN"
}
(out/"receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
print("ANDROID_B2C_PHYSICAL_SCOPE_REAL_HOST_SOCKET_PASS_ANDROID_NETD_RUNTIME_NOT_RUN")
PY
