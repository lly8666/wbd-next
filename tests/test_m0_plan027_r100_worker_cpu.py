"""H849 original public Stop CPU counters, no language attribution invented."""
import tempfile
import unittest
from pathlib import Path
from tools.network_harness.m0_plan027_r100_worker_cpu import read_worker

class NativeWorkerCpuTest(unittest.TestCase):
    def test_numeric_only_and_one_native_stop_marker(self):
        s=("secret fake=DO_NOT_PERSIST\n"
           "2026/11/02 V4_PUBLIC_WORKER_CPU role=client rx_thread_cpu_ns=1000000000 tx_thread_cpu_ns=3000000000\n"
           "2026/11/02 V4_PUBLIC_WORKER_CPU role=server rx_thread_cpu_ns=2000000000 tx_thread_cpu_ns=4000000000\n")
        c=read_worker(s,"client")
        self.assertEqual(c["status"],"OBSERVED_ORIGINAL_NATIVE_STOP")
        self.assertEqual(c["tracked_rust_rx_tx_cpu_s"],4)
        self.assertNotIn("DO_NOT_PERSIST",str(c))
        self.assertEqual(read_worker(s,"server")["tracked_rust_rx_tx_cpu_s"],6)
        self.assertEqual(read_worker(s+s,"client")["status"],"NOT_OBSERVED")

if __name__=="__main__":unittest.main()
