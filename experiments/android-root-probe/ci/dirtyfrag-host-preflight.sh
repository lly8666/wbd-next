#!/usr/bin/env bash
# Read-only host readiness only. No guest, no DirtyFrag execution.
set -euo pipefail
cd "$GITHUB_WORKSPACE"
mkdir -p out/dirtyfrag-host
python3 - <<'PY'
import datetime,json,os,pathlib,platform,shutil,stat
out=pathlib.Path("out/dirtyfrag-host")
try:
    st=os.stat("/dev/kvm")
    kvm=stat.S_ISCHR(st.st_mode) and os.access("/dev/kvm",os.R_OK|os.W_OK)
except OSError:
    kvm=False
arch=platform.machine()
emu=shutil.which("emulator")
reason=("HOST_NOT_ARM64" if arch not in ("aarch64","arm64") else
        "NO_ARM64_KVM" if not kvm else
        "NO_LINUX_ARM64_EMULATOR" if not emu else None)
d={
  "schema":"android16-dirtyfrag-preapril-host/v1",
  "source":os.getenv("GITHUB_SHA","LOCAL_UNCOMMITTED"),
  "branch":os.getenv("GITHUB_REF_NAME","local"),
  "observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "host_arch":arch,"host_kernel":platform.release(),
  "host_kvm_read_write":kvm,"host_emulator_path":emu,
  "snapshot_date":"2025-12-02",
  "snapshot_source_commit":"7c23968450618e94727e190d3a2ad3cf8f24adf7",
  "guest_candidate":"Android16/API36 Google Play ARM64 r07",
  "guest_archive_url":"https://dl.google.com/android/repository/sys-img/google_apis_playstore/arm64-v8a-36_r07.zip",
  "guest_archive_size_bytes":1886527965,
  "guest_archive_catalog_sha1":"5b91ef80a5eb60d7b7167528db259c2a12d20e9c",
  "guest_archive_downloaded":False,"guest_archive_verified":False,
  "guest_booted":False,"guest_kernel":"NOT_OBSERVED",
  "guest_initial_unrooted":"NOT_RUN",
  "dirtyfrag_release":"mitschud/DirtyFrag v1.10",
  "dirtyfrag_apk_sha256":"9ff05645fd239a4af2525fb74a62110e91288bf23c674b12332762dfe5846851",
  "su_manager":"tiann/KernelSU v3.3.1",
  "manager_apk_sha256":"b4a059ace71de2fa65cc7f12b1c58d55fc23ab25e057ee4230ce779742abe450",
  "exploit_executed":False,"root":"NOT_RUN","post_root_wbd":"NOT_RUN",
  "status":"ENV_BLOCKED" if reason else "READY_FOR_GUEST_PREFLIGHT",
  "reason":reason or "Host present; no image/guest/root tested",
  "scope":"Host-only provenance and KVM; Actions green means only script succeeded"
}
(out/"summary.json").write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
print(json.dumps({k:d[k] for k in ("source","host_arch","host_kvm_read_write","host_emulator_path","status","reason")},indent=2))
PY
sha256sum experiments/android-root-probe/ci/dirtyfrag-host-preflight.sh >out/dirtyfrag-host/script.sha256
