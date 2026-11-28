"""H2035 original Game4 cold source must use the NIC index, not NlMtu."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class TestOriginalGame4PhysicalIfindex(unittest.TestCase):
    def test_physical_ifindex_is_not_mtu(self):
        caller=(ROOT/"r0/go_overlay/cmd/wbd-client/m0_native_v4_windows.go").read_text(encoding="utf-8")
        game=(ROOT/"r0/go_overlay/cmd/wbd-client/m0_native_v4_game_windows.go").read_text(encoding="utf-8")
        self.assertIn("physical:=selected.physicalMTU",caller)
        self.assertIn("selected.ifindex!=underlay.InterfaceIndex",caller)
        self.assertIn("runM0NativeV4WindowsGame(ctx,o,underlay.Source4.As4(),physical,selected.ifindex,configure,planForGame,pathChanged,applied)",caller)
        self.assertNotIn("runM0NativeV4WindowsGame(ctx,o,underlay.Source4.As4(),selected.ifindex,open,planForGame,pathChanged)",caller)
        self.assertIn("physicalMTU uint32,physicalIfIndex uint32,",game)
        self.assertIn("physicalIfIndex,cfgs)",game)
        self.assertIn("o.ConnectionMTU,physicalMTU,o.TunnelMTU,o.Mode",game)
        self.assertIn("physicalIfIndex,o.Lease4.Addr(),o.TunnelMTU,group.Epoch()",game)

if __name__=="__main__":unittest.main()
