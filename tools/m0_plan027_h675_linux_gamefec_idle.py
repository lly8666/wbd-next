#!/usr/bin/env python3
"""Only add 105s no-business real-kernel idle to the previously verified H650 Game2/FEC fixture.

Original Go credential TLS, Rust authenticated Health and M4 driver remain
untouched. Any fixture drift fails before starting an endpoint.
"""
import pathlib,sys
assert len(sys.argv)==3
src=pathlib.Path(sys.argv[1]);dst=pathlib.Path(sys.argv[2])
assert src.is_file() and not dst.exists()
s=src.read_text()
def one(before,after):
    global s
    assert s.count(before)==1,(before,s.count(before))
    s=s.replace(before,after)
one('s.bind(("10.66.0.1",45901));s.settimeout(28)',
    's.bind(("10.66.0.1",45901));s.settimeout(180)')
one('# Go TLS handshakes and both native Rust/M4 driver bindings are READY.',
    '''# H675: no TUN business whatsoever for 105s after both original
# credential-TLS+Rust Game/FEC lanes are actually READY. The existing
# encrypted peer Health must retain both owners; no test controls or
# synthetic ACK/Receipt are injected.
if [[ "${WBD_PLAN027_GAME_IDLE105:-0}" == 1 ]];then
  test "$GAME_FEC" == 1 && test "$MODE" == game2-fec && test "$LOSS" == 15
  echo 'H675_REAL_GAME2_FEC6_IDLE105_BEGIN original_authenticated_tls=both kernel_raw_tun=both'
  sleep 105
  for role in client server;do
    sudo -n kill -0 "$(cat "$TMP/$role.pid")" ||
      { echo "H675_REAL_GAME2_FEC6_OWNER_EXITED_DURING_IDLE role=$role" >&2;exit 1; }
    if grep -q 'WBD_M0_NATIVE_HEALTH_TIMEOUT' "$TMP/$role.log";then
      echo "H675_REAL_GAME2_FEC6_FALSE_AUTH_DEAD_ON_ZERO_BUSINESS role=$role" >&2
      exit 1
    fi
  done
  echo 'H675_REAL_GAME2_FEC6_IDLE105_OWNER_BOTH_ALIVE_NO_FALSE_DEAD'
fi
# Go TLS handshakes and both native Rust M4 driver bindings are READY.''')
dst.write_text(s);dst.chmod(0o755)
print("H675_EXACT_H650_REAL_PRODUCT_FIXTURE_105S_IDLE_STAGED_NOT_A_PASS")
