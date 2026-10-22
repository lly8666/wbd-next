#!/usr/bin/env python3
"""Windows Npcap 1.88 <-> real WSL2 Ethernet. ENV QUALIFICATION ONLY.

Both directions MUST cross the real Windows NPF adapter and Linux AF_PACKET
socket. Never substitute loopback/mock/TCP for missing Npcap vEthernet.
Only a uniquely marked experimental ethertype 0x88b5 is used; no production
route/DNS/WFP modifications. The caller verifies a signed Npcap kernel service.
"""
import ctypes as c
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ETHTYPE = b"\x88\xb5"
MARK = b"WBD-WL-EXACT-REAL-NPF-WSL2-" + hashlib.sha256(os.getenv("GITHUB_SHA", "").encode()).digest()[:12]


def ps_one(script):
    p = subprocess.run(["pwsh", "-NoProfile", "-NonInteractive", "-Command", script],
                       text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=18)
    if p.returncode:
        raise RuntimeError("Windows native NIC discovery failed: " + p.stderr[-500:])
    return json.loads(p.stdout)


def wsl_python(source, *args, timeout=40):
    p = subprocess.run(["wsl.exe", "-d", "Ubuntu", "-u", "root", "--", "python3", "-c", source, *args],
                       capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError("Linux WSL2 native AF_PACKET failed: " + p.stderr[-600:])
    return p.stdout


def mac_bytes(value):
    parts = value.replace("-", ":").split(":")
    if len(parts) != 6:
        raise ValueError("unexpected native MAC address format")
    return bytes(int(x, 16) for x in parts)


def main():
    report = Path("result/wl-driver/pcap-native.json")
    status = {"source_sha": os.environ["GITHUB_SHA"], "scope": "REAL_NPCAP_WSL2_KERNEL_ETHERNET_ONLY",
              "linux_to_windows": "NOT_RUN", "windows_to_linux": "NOT_RUN",
              "product_go_tls_rust": "NOT_RUN", "wl_n0_n1_n5": "NOT_RUN"}
    try:
        adapter = ps_one("$a=@(Get-NetAdapter -IncludeHidden -ErrorAction Stop | "
                         "Where-Object {$_.Name -match 'WSL' -and $_.InterfaceGuid -ne $null}); "
                         "if($a.Count -ne 1){throw ('Require ONE WSL vEthernet; found '+$a.Count)}; "
                         "$a[0] | Select-Object Name,InterfaceGuid,MacAddress,Status | ConvertTo-Json -Compress")
        if adapter.get("Status") not in ("Up", "Connected"):
            raise RuntimeError("WSL Windows virtual NIC not UP")
        guid = str(adapter["InterfaceGuid"]).strip("{}").upper()
        device = "\\Device\\NPF_{" + guid + "}"
        win_mac = mac_bytes(adapter["MacAddress"])
        linux_info = json.loads(wsl_python(
            "import json,subprocess;"
            "x=json.loads(subprocess.check_output(['ip','-j','link','show','dev','eth0']));"
            "assert len(x)==1;print(json.dumps({'mac':x[0]['address']}))"))
        linux_mac = mac_bytes(linux_info["mac"])
        if win_mac == linux_mac or not linux_mac or win_mac == bytes(6):
            raise RuntimeError("untrusted WSL/Windows Ethernet MAC binding")
        dllpath = os.path.join(os.environ["WINDIR"], "System32", "Npcap", "wpcap.dll")
        if not os.path.isfile(dllpath):
            raise RuntimeError("Npcap official wpcap.dll not installed")
        lib = c.WinDLL(dllpath)
        lib.pcap_open_live.argtypes = [c.c_char_p, c.c_int, c.c_int, c.c_int, c.c_void_p]
        lib.pcap_open_live.restype = c.c_void_p
        lib.pcap_next_ex.argtypes = [c.c_void_p, c.POINTER(c.c_void_p), c.POINTER(c.c_void_p)]
        lib.pcap_next_ex.restype = c.c_int
        lib.pcap_sendpacket.argtypes = [c.c_void_p, c.c_void_p, c.c_int]
        lib.pcap_sendpacket.restype = c.c_int
        lib.pcap_datalink.argtypes = [c.c_void_p]
        lib.pcap_datalink.restype = c.c_int
        lib.pcap_geterr.argtypes = [c.c_void_p]
        lib.pcap_geterr.restype = c.c_char_p
        lib.pcap_close.argtypes = [c.c_void_p]
        lib.pcap_close.restype = None
        errbuf = c.create_string_buffer(512)
        handle = lib.pcap_open_live(device.encode("ascii"), 2048, 1, 100,
                                    c.cast(errbuf, c.c_void_p))
        if not handle:
            raise RuntimeError("native pcap_open_live WSL vEthernet: " + errbuf.value.decode(errors="replace"))
        try:
            if lib.pcap_datalink(handle) != 1:
                raise RuntimeError("physical NPF vEthernet is not DLT_EN10MB")
            # Linux -> Windows: actual AF_PACKET send, pcap_next_ex in Windows.
            linux_to_win = """
import socket,sys
dst=bytes.fromhex(sys.argv[1]);src=bytes.fromhex(sys.argv[2])
mark=bytes.fromhex(sys.argv[3])
s=socket.socket(socket.AF_PACKET,socket.SOCK_RAW);s.bind(('eth0',0))
n=s.send(dst+src+bytes.fromhex('88b5')+mark)
assert n==14+len(mark), (n,len(mark))
print('LINUX_RAW_ETHERNET_SENT='+str(n))
"""
            print(wsl_python(linux_to_win, win_mac.hex(), linux_mac.hex(), MARK.hex(), timeout=25).strip())
            until = time.monotonic() + 7
            got = False
            header = c.c_void_p()
            payload = c.c_void_p()
            while time.monotonic() < until:
                rc = lib.pcap_next_ex(handle, c.byref(header), c.byref(payload))
                if rc == 0:
                    continue
                if rc != 1:
                    raise RuntimeError("native pcap_next_ex error=" + str(rc))
                caplen = c.c_uint32.from_address(header.value+8).value
                if caplen < 14 or caplen > 2048:
                    continue
                wire = c.string_at(payload.value, caplen)
                if wire[:6] == win_mac and wire[6:12] == linux_mac and wire[12:14] == ETHTYPE and wire[14:] == MARK:
                    got = True
                    break
            if not got:
                raise RuntimeError("native Windows pcap did not capture authentic WSL2 AF_PACKET frame")
            status["linux_to_windows"] = "PASS_REAL_LINUX_AF_PACKET_TO_WINDOWS_NPF"
            # Windows -> Linux: reverse receives on real Linux packet socket.
            python_rx = """
import socket,sys,time
mark=bytes.fromhex(sys.argv[1]);win=bytes.fromhex(sys.argv[2]);linux=bytes.fromhex(sys.argv[3])
s=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x88b5))
s.bind(('eth0',0));s.settimeout(6)
print('AF_PACKET_LISTENER_READY',flush=True)
while True:
    data=s.recv(2048)
    if len(data)>=14 and data[:6]==linux and data[6:12]==win and data[12:14]==bytes.fromhex('88b5') and data[14:]==mark:
        print('REAL_WINDOWS_NPF_TO_LINUX_AF_PACKET='+str(len(data)),flush=True)
        break
"""
            receiver = subprocess.Popen(
                ["wsl.exe", "-d", "Ubuntu", "-u", "root", "--", "python3", "-u", "-c",
                 python_rx, MARK.hex(), win_mac.hex(), linux_mac.hex()],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                # Starting the WSL process and registering its AF_PACKET socket can take
                # several hundred ms; unique mark avoids untrusted traffic acceptance.
                time.sleep(1.4)
                frame = win_mac + linux_mac  # overwritten explicitly, no spoofed WSL peer identity.
                frame = linux_mac + win_mac + ETHTYPE + MARK
                buf = c.create_string_buffer(frame)
                rc = lib.pcap_sendpacket(handle, c.cast(buf, c.c_void_p), len(frame))
                if rc != 0:
                    err = lib.pcap_geterr(handle)
                    raise RuntimeError("real pcap_sendpacket failed: " + repr(err))
                output, errors = receiver.communicate(timeout=12)
                if receiver.returncode != 0 or "REAL_WINDOWS_NPF_TO_LINUX_AF_PACKET=" not in output:
                    raise RuntimeError("WSL Linux did not authenticate Windows NPF frame: "+str(output)+" "+str(errors[-300:]))
                status["windows_to_linux"] = "PASS_REAL_WINDOWS_NPF_TO_LINUX_AF_PACKET"
            finally:
                if receiver.poll() is None:
                    receiver.kill()
                    receiver.communicate(timeout=5)
        finally:
            lib.pcap_close(handle)
    except Exception as e:
        status["failure"] = str(e)[:700]
        print("WL_REAL_NPCAP_NATIVE_BLOCKED: " + str(e), file=sys.stderr)
    finally:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    if status["linux_to_windows"].startswith("PASS") and status["windows_to_linux"].startswith("PASS"):
        print("WL_BIDIRECTIONAL_REAL_NPCAP_WSL2_ETHERNET_PASS_ENV_ONLY")
    else:
        print("WL_BIDIRECTIONAL_REAL_NPCAP_WSL2_ETHERNET_BLOCKED_ENV_ONLY")


if __name__ == "__main__":
    main()
