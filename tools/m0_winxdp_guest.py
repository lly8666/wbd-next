"""Real Linux UDP receipt for the isolated WinXDP carrier probe."""
import socket
import sys
host, port = sys.argv[1], int(sys.argv[2])
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.connect((host, port))
    s.settimeout(4)
    for base in range(0,64,16):
        expected = {i.to_bytes(4,"big") + bytes([i])*1020 for i in range(base,base+16)}
        for packet in expected:
            s.send(packet)
        print(f"SENT={base+16}",flush=True)
        while expected:
            try:
                packet=s.recv(2048)
            except TimeoutError:
                print(f"RECEIVED={base+16-len(expected)}",flush=True)
                raise
            expected.remove(packet)
print("REAL_GUEST_RECEIPT=64/64")
