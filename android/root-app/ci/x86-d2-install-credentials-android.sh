#!/system/bin/sh
# CI-ONLY: root invokes this fixed source script AFTER KernelSU Manager grant.
# Inputs are ephemeral files, NEVER process argv, app Intent or logged output.
# Runs as real uid 0 under Android's native shell, no nested adb shell expansion.
set -eu
if [ "$(id -u)" != 0 ];then
  echo D2_CI_ROOT_GRANT_NOT_PROVEN >&2;exit 30
fi
d=/data/user/0/org.wbdnext.rootclient/files
if [ ! -d "$d" ] || [ -L "$d" ];then
  echo D2_CI_APP_PRIVATE_FILES_DIR_MISSING >&2;exit 31
fi
u="$(stat -c %u "$d")" || {
  echo D2_CI_APP_UID_STAT_UNAVAILABLE >&2;exit 32;
}
case "$u" in
  ''|*[!0-9]*) echo D2_CI_APP_UID_NOT_NUMERIC >&2;exit 33 ;;
esac
if [ "$u" -lt 10000 ] || [ "$u" -gt 1999999 ];then
  echo D2_CI_APP_UID_NOT_ORDINARY >&2;exit 34
fi
s1=/data/local/tmp/wbd-d2-pass.tmp
s2=/data/local/tmp/wbd-d2-route.tmp
s3=/data/local/tmp/wbd-d2-ca.tmp
# Failure must not retain transient CI credentials in shared local/tmp.
trap 'rm -f "$s1" "$s2" "$s3"' EXIT
for s in "$s1" "$s2" "$s3";do
  if [ ! -f "$s" ] || [ -L "$s" ];then
    echo D2_CI_EPHEMERAL_SECRET_SOURCE_INVALID >&2;exit 35
  fi
done
for f in wbd-pass.secret wbd-route.secret wbd-server-ca.pem;do
  if [ -L "$d/$f" ];then
    echo D2_CI_APP_SECRET_TARGET_SYMLINK >&2;exit 36
  fi
done
# The real RootClientService will read these exact 0600 files with O_NOFOLLOW.
# It owns deletion after original Go returns. No ci-only bypass in product.
cp "$s1" "$d/wbd-pass.secret" || exit 37
cp "$s2" "$d/wbd-route.secret" || exit 38
cp "$s3" "$d/wbd-server-ca.pem" || exit 39
chown "$u:$u" "$d/wbd-pass.secret" "$d/wbd-route.secret" "$d/wbd-server-ca.pem" || exit 40
chmod 600 "$d/wbd-pass.secret" "$d/wbd-route.secret" "$d/wbd-server-ca.pem" || exit 41
for f in wbd-pass.secret wbd-route.secret wbd-server-ca.pem;do
  if [ "$(stat -c %u "$d/$f")" != "$u" ] ||
     [ "$(stat -c %a "$d/$f")" != 600 ];then
    echo D2_CI_APP_SECRET_OWNERSHIP_OR_MODE_NOT_PROVEN >&2;exit 42
  fi
done
echo D2_CI_APP_PRIVATE_SECRET_STAGING_PASS
