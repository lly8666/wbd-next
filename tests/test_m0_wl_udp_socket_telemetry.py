"""Linux UDP fixture-level drop attribution without production side effects."""
import unittest
import tempfile
from pathlib import Path
from tools.m0_wl_udp_socket_telemetry import parse_udp_mib,parse_udp_socket,delta,parse_linux_raw_sockets,raw_sockets_delta,raw_socket_product_owners

class LinuxUdpSocketTelemetryTests(unittest.TestCase):
    def test_windows_host_ipv4_udp_not_per_socket_and_wrap_fails_closed(self):
        import ctypes
        from tools.m0_wl_udp_socket_telemetry import _windows_udp_ipv4_stats
        def fake(ptr):
            words=(ctypes.c_uint32*5).from_address(ctypes.cast(ptr,ctypes.c_void_p).value)
            words[0]=100;words[1]=4;words[2]=7;words[3]=140;words[4]=2
            return 0
        self.assertEqual(_windows_udp_ipv4_stats(fake),
                         {"in_datagrams":100,"no_ports":4,"in_errors":7})
        a={"windows_host_ipv4_udp_stats":{"in_datagrams":10,"no_ports":0,"in_errors":2}}
        b={"windows_host_ipv4_udp_stats":{"in_datagrams":30,"no_ports":4,"in_errors":7}}
        self.assertEqual(delta(a,b)["windows_host_ipv4_udp_deltas"],
                         {"in_datagrams_delta":20,"in_errors_delta":5,"no_ports_delta":4})
        self.assertIsNone(delta(b,a)["windows_host_ipv4_udp_deltas"]["in_errors_delta"])
        self.assertIsNone(delta({},{}).get("windows_host_ipv4_udp_deltas"))

    def test_exact_socket_inode_not_other_udp_apps(self):
        header="sl local_address rem_address st tx_queue tr tm->when retrnsmt uid timeout inode ref pointer drops"
        line1="1: 0100007F:B34F 00000000:0000 07 00000000:0000ABCD 00:00000000 00000000 0 0 1234 2 00000000 57"
        line2="2: 0100007F:B350 00000000:0000 07 00000000:00000000 00:00000000 00000000 0 0 9999 2 00000000 9"
        r=parse_udp_socket("\n".join([header,line1,line2]),1234)
        self.assertEqual(r,{"rx_queue_bytes":43981,"socket_drops":57})
    def test_no_socket_is_not_zero_drops(self):
        self.assertIsNone(parse_udp_socket("sl local\n",1234))
    def test_mib_scope_is_linux_guest_global(self):
        s="Ip: A B\nIp: 1 2\nUdp: InDatagrams InErrors RcvbufErrors\nUdp: 1000 23 19\n"
        self.assertEqual(parse_udp_mib(s)["RcvbufErrors"],19)
    def test_missing_or_reset_is_unknown(self):
        self.assertIsNone(delta({"linux_socket_udp_drops":34},{"linux_socket_udp_drops":20})["linux_socket_udp_drops_delta"])
        self.assertIsNone(delta({}, {})["linux_guest_global_udp_rcvbuf_errors_delta"])
    def test_raw_socket_by_exact_inode_drop_delta(self):
        h="sl local remote st tx_queue tr tm retrnsmt uid timeout inode ref pointer drops"
        first=parse_linux_raw_sockets(h+"\n1: 00000000:0006 00000000:0000 07 00000000:00000005 00:00000000 00000000 0 0 4321 2 abc 300\n")
        last=parse_linux_raw_sockets(h+"\n1: 00000000:0006 00000000:0000 07 00000000:00001000 00:00000000 00000000 0 0 4321 2 abc 103300\n")
        self.assertEqual(raw_sockets_delta(first,last)["4321"]["drops_delta"],103000)
        self.assertEqual(last["4321"]["rx_queue_bytes"],4096)
    def test_raw_socket_replaced_is_unknown(self):
        self.assertIsNone(raw_sockets_delta({"123":{"drops":1}},{"456":{"drops":9}}))

    def test_real_proc_fd_owner_exact_inode_not_name_guess(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            p=root/"321"
            (p/"fd").mkdir(parents=True)
            (p/"comm").write_text("wbd-v4-server\n")
            (p/"fd"/"4").symlink_to("socket:[9367]")
            q=root/"654"
            (q/"fd").mkdir(parents=True)
            (q/"comm").write_text("unrelated\n")
            (q/"fd"/"3").symlink_to("socket:[9911]")
            owners=raw_socket_product_owners({"9367","9911"},proc_root=root)
            self.assertEqual(owners,{"9367":{"pid":321,"comm":"wbd-v4-server",
                "identity":"EXACT_PROC_FD_SOCKET_INODE"}})

    def test_monotonic_drop_is_actual_delta(self):
        x=delta({"linux_socket_udp_drops":3},{"linux_socket_udp_drops":77})
        self.assertEqual(x["linux_socket_udp_drops_delta"],74)

if __name__=="__main__":unittest.main()
