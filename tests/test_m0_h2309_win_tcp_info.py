"""H2309 actual OS send-side TCP cwnd/RTO instrumentation must be read-only."""
import ctypes,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import m0_h2309_win_tcp_info as info
class H2309TrueKernelSendTCPInfo(unittest.TestCase):
    def test_microsoft_tcp_info_v0_abi_is_exact_and_read_only(self):
        self.assertEqual(info.SIO_TCP_INFO,0xD8000027)
        self.assertEqual(ctypes.sizeof(info.TCP_INFO_v0),88)
        self.assertEqual(info.TCP_INFO_v0.Cwnd.offset,32)
        self.assertEqual(info.TCP_INFO_v0.BytesRetrans.offset,68)
        self.assertEqual(info.TCP_INFO_v0.TimeoutEpisodes.offset,80)
        code=(ROOT/"tools/m0_h2309_win_tcp_info.py").read_text()
        for term in ("WSAIoctl","SIO_TCP_INFO","read_original_socket_tcp_info",
                     "BytesInFlight","Cwnd","SndWnd","BytesRetrans",
                     "TimeoutEpisodes","RttUs"):
            self.assertIn(term,code)
        for disallowed in (".sendall(",".sendto(",".setsockopt("):
            self.assertNotIn(disallowed,code)
    def test_client_samples_real_socket_and_preserves_failure_artifacts(self):
        src=(ROOT/"tools/m0_wl_loss_tcp_probe.py").read_text()
        wrap=(ROOT/"tools/m0_h2286_full_windows_product.py").read_text()
        for term in ("WBD_H2309_WIN_TCP_INFO","CLIENT_SENDER_TCP_INFO",
                     "per_bulk_flow","observer_stop.wait(2)","len(win_tcpinfo[flow_index])>=140"):
            self.assertIn(term,src)
        for term in ("h2309_original_windows_sender_tcp_info",
                     "h2309_real_windows_tcp_info_failure",
                     "row.get(\"AppliedSetting\") in (0,1"):
            self.assertIn(term,wrap)
    def test_two_original_bbr2_fec_off_loss1_loss5_three_runner_ci(self):
        self.assertIn("H2308_WINDOWS_ORIGINAL_TCP_CC_RESTORED",
                      (ROOT/"tools/m0_h2308_windows_cc.ps1").read_text())
        for loss in (1,5):
            wf=(ROOT/f".github/workflows/qa-h2309-bbr2-tcpinfo-loss{loss}.yml").read_text()
            for term in (f'WBD_H2293_WEAK_LOSS_PCT: "{loss}"',
                         'WBD_H2308_WIN_BBR2: "1"',
                         'WBD_H2309_WIN_TCP_INFO: "1"',
                         'WBD_H2302_WINDOW_ABA: "1"',
                         'WBD_H2294_OFF_REPAIR_ABA: "0"',
                         f'[m0-029-h2309-bbr2-tcpinfo-loss{loss}]',
                         "REAL_TWO_KERNEL_NETEM_EGRESS_DIRECTIONS_CONFIRMED",
                         "H2302_REAL_ARM_TUN_THREE_FEC_OFF_TCP_STAGES_DONE",
                         "H2308 always restore Windows TCP",
                         "client_owned_stop","original_rust_binary_identical_all_legs"):
                self.assertIn(term,wf)
if __name__=="__main__":
    unittest.main()
