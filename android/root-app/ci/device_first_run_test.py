#!/usr/bin/env python3
"""No-device, no-root tests for the operator-only ARM64 acceptance utility."""
import pathlib
import tempfile
import unittest
import zipfile
import hashlib
import json
import struct

import device_first_run as d


class FirstRunTests(unittest.TestCase):
    def test_actual_arm64_kernel_not_advertised_nativebridge(self):
        self.assertEqual(d.parse_devices("List of devices attached\nserialA device product:x\nserialB unauthorized\n"), ["serialA"])
        self.assertFalse(d.verify_elf(b""))
        elf = bytearray(120)
        elf[:5] = b"\x7fELF\x02"
        struct.pack_into("<H", elf, 18, 183)
        struct.pack_into("<Q", elf, 32, 64)
        struct.pack_into("<HH", elf, 54, 56, 1)
        struct.pack_into("<I", elf, 64, 1)
        struct.pack_into("<Q", elf, 64+48, 16384)
        self.assertTrue(d.verify_elf(bytes(elf)))
        struct.pack_into("<H", elf, 18, 62)
        self.assertFalse(d.verify_elf(bytes(elf)))
        struct.pack_into("<H", elf, 18, 183)
        struct.pack_into("<Q", elf, 64+48, 4096)
        self.assertFalse(d.verify_elf(bytes(elf)))

    def test_receipts_are_fixed_enum_only(self):
        raw = ("11-18 09:00:00.123 I WBD_ROOT_DIAG: START_REQUESTED\n"
               "11-18 09:00:01.123 I WBD_ROOT_DIAG: NATIVE_M4_AND_UID_READY\n"
               "11-18 09:00:01.456 I WBD_ROOT_DIAG: PASSWORD_SECRETX\n"
               "11-18 09:00:01.999 W unrelated: user=alice@example.com\n")
        self.assertEqual(d.parse_events(raw),
                         ["START_REQUESTED", "NATIVE_M4_AND_UID_READY"])
        self.assertEqual(d.new_events(["A", "B"], ["B", "C"]), ["C"])
        self.assertEqual(d.new_events(["A", "B"], ["Q", "R"]), [])
        self.assertEqual(d.new_events([], ["START_REQUESTED"]), ["START_REQUESTED"])

    def test_only_private_route_metadata(self):
        raw = ("0: from all lookup local\n"
               "9600: from all uidrange 10142-10142 lookup 19842\n"
               "9608: from all lookup main\n"
               "32766: from all lookup 19842\n"
               "22000: from 192.0.2.33 lookup default\n")
        owned = d.owned_rules(raw)
        self.assertEqual([x["priority"] for x in owned], [9600, 32766])
        self.assertTrue(all("uid" not in x and "192." not in str(x) for x in owned))
        self.assertEqual(d.owned_rules("0: from all lookup local\n"), [])

    def test_never_credit_android_e2e_or_stop_just_from_ui(self):
        e = ["START_REQUESTED", "NETWORK_SCOPE_VERIFIED",
             "APP_UID_GROUP_VERIFIED", "NATIVE_M4_AND_UID_READY"]
        report = d.summarize([], e, e, [], [], True)
        self.assertEqual(report["original_m4_and_uid_receipt"], "PASS")
        self.assertEqual(report["real_android_linux_tls_and_data_e2e"], "NOT_RUN")
        self.assertEqual(report["owned_kernel_routes_after_stop"], "NOT_RUN")
        e2 = e + ["STOP_REQUESTED", "STOP_SIGNAL_ACCEPTED",
                  "ROOT_PROCESS_EXIT_ZERO", "OWNER_CLEANUP_FINISHED"]
        report = d.summarize([], e, e2, [], [], True)
        self.assertEqual(report["owned_kernel_routes_after_stop"], "PASS")
        self.assertEqual(report["original_go_rust_joined_stop"], "NOT_RUN")
        authentic=e + ["AUTHENTICATED_LEASE_OS_READBACK",
                       "ORIGINAL_GO_RUST_HANDOFF"]
        verified_stop=authentic + ["STOP_REQUESTED", "STOP_SIGNAL_ACCEPTED",
                                 "ORIGINAL_GO_UID_ROUTE_STOP_DRAINED",
                                 "ORIGINAL_GO_RUST_STOP_JOINED",
                                 "ROOT_PROCESS_EXIT_ZERO", "OWNER_CLEANUP_FINISHED"]
        report=d.summarize([], authentic, verified_stop, [], [], True)
        self.assertEqual(report["original_go_rust_joined_stop"],"PASS")
        self.assertEqual(report["original_tls_authenticated_lease_os_readback"],"PASS")
        self.assertEqual(report["real_android_linux_tls_and_data_e2e"],"NOT_RUN")
        with_signal_only=authentic+["STOP_REQUESTED","STOP_SIGNAL_ACCEPTED",
                                    "ROOT_PROCESS_EXIT_ZERO"]
        report=d.summarize([],authentic,with_signal_only,[],[],True)
        self.assertEqual(report["original_go_rust_joined_stop"],"NOT_RUN")
        report = d.summarize([], e, e2, [], [{"priority":9600}], True)
        self.assertEqual(report["owned_kernel_routes_after_stop"], "FAIL")
        report = d.summarize([], e, e2, None, [], True)
        self.assertEqual(report["owned_kernel_routes_after_stop"], "NOT_RUN")

    def test_apk_assets_source_lock_and_no_diagnostic_leak(self):
        raw = bytearray(120)
        raw[:5] = b"\x7fELF\x02"
        struct.pack_into("<H", raw, 18, 183)
        struct.pack_into("<Q", raw, 32, 64)
        struct.pack_into("<HH", raw, 54, 56, 1)
        struct.pack_into("<I", raw, 64, 1)
        struct.pack_into("<Q", raw, 64+48, 16384)
        elf = bytes(raw)
        source = "a"*40
        base = "assets/native-arm64/"
        meta = {"source":source, "artifacts":{
            x:{"sha256": hashlib.sha256(elf).hexdigest()}
            for x in ("wbd-v4-client-arm64","libwbd_engine-arm64.so")}}
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td)/"app.apk"
            with zipfile.ZipFile(path,"w") as z:
                z.writestr(base+"SOURCE",source+"\n")
                z.writestr(base+"manifest.json",json.dumps(meta))
                for filename in meta["artifacts"]:
                    z.writestr(base+filename,elf)
            self.assertEqual(d.inspect_apk(path)["same_source_arm64_16k_assets"],"PASS")
            self.assertEqual(d.inspect_apk(path)["apk_signature_verified_here"],"NOT_RUN")
            with zipfile.ZipFile(path,"a") as z:
                z.writestr("assets/native-arm64/x86-probe",b"bad")
            with self.assertRaises(ValueError):
                d.inspect_apk(path)

    def test_owned_route_table_and_tun_missing_are_distinct(self):
        class Fixture(d.Device):
            def __init__(self, rows):
                self.rows=rows
            def shell(self,*args):
                return self.rows[args]

        normal_rules=("ip","-4","rule","show")
        normal_table=("ip","-4","route","show","table","19842")
        normal_tun=("ip","link","show","dev","wbdv40")
        normal={
            normal_rules:(0,"0: from all lookup local\n",""),
            normal_table:(2,"","Error: ipv4: FIB table does not exist."),
            normal_tun:(1,"","Device \"wbdv40\" does not exist.")
        }
        self.assertEqual(Fixture(normal).route_rules(),[])
        with_tun=dict(normal)
        with_tun[normal_tun]=(0,"102: wbdv40: <POINTOPOINT> mtu 1400\n","")
        self.assertEqual(Fixture(with_tun).route_rules()[0]["priority"],-2)
        with_table=dict(normal)
        with_table[normal_table]=(0,"10.66.0.0/24 dev wbdv40\n","")
        self.assertEqual(Fixture(with_table).route_rules()[0]["priority"],-1)
        unreadable=dict(normal)
        unreadable[normal_table]=(1,"","Permission denied")
        self.assertIsNone(Fixture(unreadable).route_rules())

    def test_private_output_has_only_filtered_data(self):
        with tempfile.TemporaryDirectory() as td:
            folder=pathlib.Path(td)/"acceptance"
            zipfile_path=d.write_bundle(folder,{"result":{"allowlisted_events":["START_REQUESTED"]}})
            with zipfile.ZipFile(zipfile_path) as z:
                self.assertEqual(z.namelist(),["acceptance.json"])
                raw=z.read("acceptance.json").decode()
                self.assertNotIn("secret",raw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
