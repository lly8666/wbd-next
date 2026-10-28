import unittest
from tools import m0_wl_native_resource_sampler as sampler

class NativeThreadCPUContract(unittest.TestCase):
    def test_thread_entry_matches_win32_layout(self):
        self.assertEqual(sampler.ctypes.sizeof(sampler._ThreadEntry),28)
    def test_100ns_native_windows_thread_cpu_conversion(self):
        x=sampler._FileTime()
        x.low=10_000_000;x.high=0
        self.assertAlmostEqual(sampler._sec(x),1.0)
if __name__=="__main__":unittest.main()
