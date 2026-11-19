#!/usr/bin/env python3
"""H2221 real isolated kernel contract: AF_PACKET L3 survives raw PREROUTING DROP.
Proves packet visibility only, not product/TLS/AEAD or physical NAT.
"""
import json, os, select, socket, struct, subprocess, sys, time
CL, SV, CI, SI = "h2221-cl", "h2221-sv", "h2221-c", "h2221-s"
SRC, DST = "10.246.21.1", "10.246.21.2"

def run(*cmd, check=True):
    return subprocess.run(cmd, capture_output=True, text=True, check=check)

def valid(b):
    return len(b) >= 40 and b[0] >> 4 == 4 and b[9] == 6 \
        and b[12:16] == socket.inet_aton(SRC) \
        and b[16:20] == socket.inet_aton(DST) \
        and b[22:24] == struct.pack("!H", 443)

def listen():
    packet = socket.socket(socket.AF_PACKET, socket.SOCK_DGRAM, socket.htons(0x0800))
    # Python bind() expects ETH_P_IP in host order; the socket() syscall does not.
    packet.bind((SI, 0x0800))
    raw = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
    raw.bind((DST, 0))
    packet.setblocking(False)
    raw.setblocking(False)
    print("READY", flush=True)
    count = {"packet_l3":0, "ipproto_tcp":0}
    end = time.monotonic()+1.7
    while time.monotonic() < end:
        for s in select.select([packet, raw], [], [], .1)[0]:
            try: frame = s.recv(2048)
            except BlockingIOError: continue
            if valid(frame): count["packet_l3" if s is packet else "ipproto_tcp"] += 1
    print(json.dumps(count), flush=True)

def send():
    for i in range(5):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(.06)
        s.bind((SRC, 40017+i))
        try: s.connect((DST, 443))
        except OSError: pass
        s.close()
        time.sleep(.04)
    print("SENT=5", flush=True)

def trial():
    p = subprocess.Popen(["ip","netns","exec",SV,sys.executable,"-u",__file__,"listen"],
                         stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    assert p.stdout.readline().strip() == "READY", "listener failed"
    out = run("ip","netns","exec",CL,sys.executable,__file__,"send")
    assert "SENT=5" in out.stdout, out
    output, error = p.communicate(timeout=8)
    assert p.returncode == 0, error
    return json.loads(output.splitlines()[-1])

def main():
    assert os.geteuid() == 0
    try:
        run("ip","netns","add",CL)
        run("ip","netns","add",SV)
        run("ip","link","add",CI,"type","veth","peer","name",SI)
        run("ip","link","set",CI,"netns",CL)
        run("ip","link","set",SI,"netns",SV)
        for ns,dev,ip in ((CL,CI,SRC),(SV,SI,DST)):
            run("ip","-n",ns,"addr","add",ip+"/30","dev",dev)
            run("ip","-n",ns,"link","set",dev,"up")
            run("ip","-n",ns,"link","set","lo","up")
        before = trial()
        assert before["packet_l3"] > 0 and before["ipproto_tcp"] > 0, before
        run("ip","netns","exec",SV,"iptables","-t","raw","-I","PREROUTING",
            "1","-p","tcp","--dport","443","-j","DROP")
        after = trial()
        assert after["packet_l3"] > 0 and after["ipproto_tcp"] == 0, after
        print(json.dumps({"baseline":before,"prerouting_drop":after,
              "qualification":"PASS_SCOPED_KERNEL_VISIBILITY_ONLY"}),flush=True)
    finally:
        run("ip","netns","del",CL,check=False)
        run("ip","netns","del",SV,check=False)

if __name__ == "__main__":
    {"listen":listen,"send":send}.get(sys.argv[1] if len(sys.argv)>1 else "",main)()
