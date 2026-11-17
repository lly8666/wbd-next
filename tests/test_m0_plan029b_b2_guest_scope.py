import ast
import unittest
from pathlib import Path


class B2GuestExactTicketScope(unittest.TestCase):
    def test_unrelated_os_query_is_only_bounded_tunnel_non_test_ticket(self):
        root = Path(__file__).resolve().parents[1]
        guest = (root / "tools/m0_plan029b_b2_cn_guest.py").read_text(
            encoding="utf-8")
        win = (root / "tools/m0_plan029b_b2_cn_windows.py").read_text(
            encoding="utf-8")
        self.assertIn('query("cn", CN, "8.8.8.8", 0x6201)', win)
        self.assertIn('query("global", GLOBAL, tunnel_dns, 0x6202)', win)
        self.assertIn('if peer[0] != expected:', guest)
        self.assertIn('if label == "global_dns" and len(wire) >= 12', guest)
        self.assertIn('wire[:2] != b"\\x62\\x02"', guest)
        self.assertIn('wire[12:] not in (CN + A, GLOBAL + A)', guest)
        self.assertIn('if unrelated_tunnel_dns > 4:', guest)
        self.assertIn('if label == "global_dns" and wire[12:] == GLOBAL + A', guest)
        self.assertIn('if attempts > 2:', guest)
        self.assertIn('if wire not in markers or wire.decode() in seen:', guest)
        self.assertIn('if set(seen) != {"cn_dns", "global_dns",', guest)
        self.assertIn('"unrelated_tunnel_dns": unrelated_tunnel_dns', guest)
        # Parse the genuine Python AST: a doubled backslash in source
        # creates ASCII bytes \\x62, not the DNS ID 0x6202.
        byte_literals = {node.value for node in ast.walk(ast.parse(guest))
                         if isinstance(node, ast.Constant)
                         and isinstance(node.value, bytes)}
        self.assertIn(bytes.fromhex("6202"), byte_literals)
        self.assertIn(bytes.fromhex("01000001"), byte_literals)
        self.assertNotIn(bytes([92, 120, 54, 50, 92, 120, 48, 50]), byte_literals)

        # Product and fixture physical-CN QNAME continue to fail closed.
        self.assertIn('raise RuntimeError("B2 wrong real upstream domain/question")', guest)


if __name__ == "__main__":
    unittest.main()
