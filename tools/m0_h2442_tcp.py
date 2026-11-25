"""One TCP connection at a time; fixed wall-window including stalls."""
import socket,struct,sys,time,json,hashlib
def source(host,port,rate,cc,seconds):
    with socket.socket() as l:
        l.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);l.bind((host,port));l.listen(1);l.settimeout(90)
        print("SOURCE_READY",flush=True)
        c,_=l.accept()
        with c:
            c.setsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,cc.encode())
            assert c.getsockopt(socket.IPPROTO_TCP,socket.TCP_CONGESTION,32).split(b"\0")[0].decode()==cc
            if rate:c.setsockopt(socket.SOL_SOCKET,47,struct.pack("=Q",rate*125000))
            actual=struct.unpack("=Q",c.getsockopt(socket.SOL_SOCKET,47,8))[0]
            assert not rate or actual==rate*125000
            c.settimeout(15);assert c.recv(1)==b"R"
            c.settimeout(.5);b=bytes(256*1024);n=0;t=time.monotonic();end="deadline"
            while time.monotonic()-t<seconds:
                try:q=c.send(b)
                except socket.timeout:continue
                except OSError as e:end=repr(e);break
                if not q:end="zero";break
                n+=q
            try:c.shutdown(socket.SHUT_WR)
            except OSError as e:end=repr(e)
            print(json.dumps({"bytes":n,"end":end,"actual_cc":cc,"pacing_bytes_per_s":actual}),flush=True)
def sink(host,port,local,seconds):
    with socket.create_connection((host,port),timeout=30,source_address=(local,0)) as c:
        assert c.getsockname()[0]==local;c.sendall(b"R");c.settimeout(.5)
        n=steady=0;t=time.monotonic();end="deadline";b=bytearray(256*1024);last=t;lastn=0
        while time.monotonic()-t<seconds+80:
            try:q=c.recv_into(b)
            except socket.timeout:q=-1
            except OSError as e:end=repr(e);break
            now=time.monotonic();elapsed=now-t
            if q==0:end="eof";break
            if q>0:
                n+=q
                if 10<=elapsed<seconds-5:steady+=q
            if now-last>=5:
                print("TCP_PROGRESS "+json.dumps({"elapsed":round(elapsed,2),"bytes":n,"recent_mbps":(n-lastn)*8/(now-last)/1e6}),flush=True);last=now;lastn=n
        row={"bytes":n,"end":end,"rx_mbps":steady*8/(seconds-15)/1e6,"elapsed":time.monotonic()-t,"local":local}
        print(json.dumps(row),flush=True);return row
def probe(host,port):
    with socket.socket() as l:
        l.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);l.bind((host,port));l.listen(1);l.settimeout(80)
        print("PROBE_READY",flush=True)
        c,_=l.accept()
        with c:
            c.settimeout(10);assert c.recv(1)==b"R";c.sendall(b"S");assert c.recv(1)==b"T";c.sendall(b"U")
if __name__=="__main__":
    role=sys.argv[1]
    if role=="source":source(sys.argv[2],int(sys.argv[3]),int(sys.argv[4]),sys.argv[5],int(sys.argv[6]))
    elif role=="probe":probe(sys.argv[2],int(sys.argv[3]))
