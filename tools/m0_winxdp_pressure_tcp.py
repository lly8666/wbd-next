"""Actual Winsock/Linux TCP, independent sending/receiving; exact hash and bytes per flow."""
import hashlib,json,socket,sys,time,threading,os
BLOCK=bytes(range(256))*256
# Same business window; separate bounded TCP drain on both peers.
DRAIN_SECONDS=120 if os.environ.get("WBD_XDP_STRESS_PHASE") in ("carrier-abba","normal-tune") else 65
def exchange(sock,seconds,rate,send,receive,windows):
    sock.settimeout(.5)
    result={"sent":0,"received":0,"tx_sha256":"","rx_sha256":"","tx_end":"inactive","rx_end":"inactive","steady_rx_bytes":0,"max_rx_gap_s":0}
    result["socket_sndbuf"]=sock.getsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF)
    result["socket_rcvbuf"]=sock.getsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF)
    result["send_timeouts"]=0
    result["drain_budget_s"]=DRAIN_SECONDS
    result["last_rx_elapsed_s"]=None
    result["rx_eof_elapsed_s"]=None
    result["rx_after_business_bytes"]=0
    result["tx_shutdown_elapsed_s"]=None
    start=time.monotonic();errors=[]
    def tx():
        h=hashlib.sha256()
        try:
            if not windows and send and rate:
                import struct
                sock.setsockopt(socket.SOL_SOCKET,47,struct.pack("=Q",int(rate*125000)))
            deadline=start+seconds
            if send:
                while time.monotonic()<deadline:
                    if windows and rate:
                        due=start+result["sent"]/(rate*125000)
                        if due>time.monotonic():time.sleep(min(due-time.monotonic(),.02));continue
                    try:n=sock.send(BLOCK)
                    except socket.timeout:result["send_timeouts"]+=1;continue
                    if not n:raise RuntimeError("send returned zero")
                    result["sent"]+=n;h.update(BLOCK[:n])
                result["tx_end"]="deadline"
            if not send:
                while result["rx_end"]=="inactive" and time.monotonic()<start+seconds+DRAIN_SECONDS:time.sleep(.02)
            sock.shutdown(socket.SHUT_WR)
            result["tx_shutdown_elapsed_s"]=time.monotonic()-start
        except Exception as e:errors.append("tx:"+repr(e));result["tx_end"]="error"
        finally:result["tx_sha256"]=h.hexdigest()
    def rx():
        h=hashlib.sha256();buf=bytearray(262144);last=start
        try:
            while time.monotonic()<start+seconds+DRAIN_SECONDS:
                try:n=sock.recv_into(buf)
                except socket.timeout:continue
                now=time.monotonic()
                if not n:
                    result["rx_end"]="eof";result["rx_eof_elapsed_s"]=now-start;return
                result["last_rx_elapsed_s"]=now-start
                if now-start>=seconds:result["rx_after_business_bytes"]+=n
                result["received"]+=n;h.update(memoryview(buf)[:n])
                if 10<=now-start<seconds-5:
                    result["steady_rx_bytes"]+=n
                    result["max_rx_gap_s"]=max(result["max_rx_gap_s"],now-last)
                last=now
            result["rx_end"]="timeout"
        except Exception as e:errors.append("rx:"+repr(e));result["rx_end"]="error"
        finally:result["rx_sha256"]=h.hexdigest()
    t=threading.Thread(target=tx);r=threading.Thread(target=rx);t.start();r.start()
    # Join both against the SAME absolute deadline. A completed TX thread
    # must not shorten the RX drain to five seconds after the business window.
    join_deadline=start+seconds+DRAIN_SECONDS+2
    for worker in (t,r):
        worker.join(max(0,join_deadline-time.monotonic()))
    if t.is_alive() or r.is_alive():
        errors.append("exchange thread timeout")
        try:sock.shutdown(socket.SHUT_RDWR)
        except OSError:pass
        sock.close()
        for worker in (t,r):worker.join(3)
    result["errors"]=errors
    return result
def active(direction,windows):
    return ((direction!="down" if windows else direction!="up"),(direction!="up" if windows else direction!="down"))
def summarize(rows,seconds):
    return {"flows":rows,"bytes":sum(x["sent"]+x["received"] for x in rows),"sent":sum(x["sent"] for x in rows),"received":sum(x["received"] for x in rows),"rx_mbps":sum(x["steady_rx_bytes"] for x in rows)*8/(seconds-15)/1e6,"end":"eof" if all(x["rx_end"]=="eof" and x["tx_end"] in ("deadline","inactive") and not x["errors"] for x in rows) else "incomplete"}
def serve(host,port,seconds,rate,direction,streams):
    rows=[None]*streams;threads=[]
    with socket.socket() as l:
        l.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);l.bind((host,port));l.listen(streams);l.settimeout(100)
        print("SOURCE_READY",flush=True)
        def work(sock):
            with sock:
                sock.settimeout(40)
                i=int(sock.recv(1)[0]);assert 0<=i<streams
                sock.sendall(b"R")
                rows[i]=exchange(sock,seconds,rate/streams,*active(direction,False),False)
        for _ in range(streams):
            s,_=l.accept();t=threading.Thread(target=work,args=(s,));t.start();threads.append(t)
        for t in threads:t.join(seconds+DRAIN_SECONDS+35)
    assert all(x is not None for x in rows),rows
    out=summarize(rows,seconds)
    out["end"]="deadline" if out["end"]=="eof" else out["end"]
    print(json.dumps(out),flush=True)
def client(host,port,local,seconds,case,connected):
    n=case["streams"];rows=[None]*n;threads=[];socks=[]
    try:
        for i in range(n):
            sock=socket.socket()
            sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,case["rcvbuf"])
            if case.get("sndbuf"):sock.setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,case["sndbuf"])
            sock.settimeout(35);sock.bind((local,0));sock.connect((host,port));socks.append(sock)
        if connected:connected()
        def work(i,sock):
            with sock:
                sock.sendall(bytes([i]));assert sock.recv(1)==b"R"
                rows[i]=exchange(sock,seconds,case["rate"]/n,*active(case["direction"],True),True)
        for i,sock in enumerate(socks):
            t=threading.Thread(target=work,args=(i,sock));t.start();threads.append(t)
        for t in threads:t.join(seconds+DRAIN_SECONDS+35)
        assert all(x is not None for x in rows),rows
        return summarize(rows,seconds)
    finally:
        for s in socks:s.close()
if __name__=="__main__":
    serve(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),sys.argv[5],int(sys.argv[6]))
