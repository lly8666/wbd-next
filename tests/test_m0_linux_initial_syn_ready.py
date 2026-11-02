"""H982 source-locked native Linux initial SYN & AF_PACKET readiness."""
import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class LinuxNativeInitialReady(unittest.TestCase):
 def test_initial_and_reauth_syn_same_frozen_original_retry(self):
  text=(ROOT/"r0/go_overlay/internal/v4productcli/linux.go").read_text()
  self.assertIn("err=waitForOriginalColdSYN(dialCtx,assoc)",text)
  self.assertNotIn("err=assoc.WaitEstablished(dialCtx)",text)
  self.assertIn("V4_PUBLIC_RAW_AF_PACKET_READY role=%s",text)
  self.assertIn("assoc.EmitRetransmitDue(time.Now())",text)
 def test_netns_waits_real_raw_socket_not_only_tun_file(self):
  text=(ROOT/"tools/arm64_linux_netns_smoke.sh").read_text()
  self.assertIn("ARM64_REAL_GO_AF_PACKET_SERVER_LISTENING_BEFORE_SYN_PASS",text)
  self.assertIn("ARM64_OS_SERVER_RAW_LISTENER_NOT_READY_BEFORE_CLIENT_SYN",text)
if __name__=="__main__":unittest.main()
