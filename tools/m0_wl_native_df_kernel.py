"""Real native Win32 Wintun ↔ Linux TUN DF0/DF1 application sizes and TCP64K."""
import errno,json,os,pathlib,socket,sys,time,threading
SIZE=1728
PROBE_SIZES=(1728,4096,65507)
PORT=45909
TCP_PORT=45902
DF0_SMALL_ATTEMPTS=3

def payload(ip,size=SIZE):
    if type(size) is not int or not 64<=size<=65507:
        raise ValueError("invalid IPv4 UDP payload size")
    prefix=("WBD-DF0-"+ip+"-").encode("ascii")
    return prefix+bytes((i*29+7)%251 for i in range(size-len(prefix)))

def df_option(sock,enabled):
    if os.name=="nt":name,value=getattr(socket,"IP_DONTFRAGMENT",14),int(enabled)
    else:name,value=getattr(socket,"IP_MTU_DISCOVER",10),(2 if enabled else 0)
    sock.setsockopt(socket.IPPROTO_IP,name,value)
    if sock.getsockopt(socket.IPPROTO_IP,name)!=value:
        raise RuntimeError("kernel IP DF option readback mismatch")
    return (name,value)

def stage_barrier(gate,label,timeout_s=12):
    # Both OS sockets must reach precisely the same packet family before
    # either side sends; never count a different-size late packet as success.
    me="windows" if os.name=="nt" else "linux"
    other="linux" if me=="windows" else "windows"
    marker=pathlib.Path(str(gate)+"."+label+"."+me)
    peer=pathlib.Path(str(gate)+"."+label+"."+other)
    marker.write_text("REAL_NATIVE_SOCKET_READY\n")
    until=time.monotonic()+timeout_s
    while not peer.is_file():
        if time.monotonic()>until:
            raise RuntimeError("genuine opposite OS stage barrier missing: "+label)
        time.sleep(.04)
    print(json.dumps({"phase":"stage_barrier","name":label,"os":me}),flush=True)

def tcp64k(local,remote,gate):
    listen=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    listen.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    listen.bind((local,TCP_PORT));listen.listen(1);listen.settimeout(10)
    issues=[];received=[]
    def serve():
        try:
            conn,peer=listen.accept()
            with conn:
                conn.settimeout(10)
                expected=payload(remote,65507)+bytes(29)
                data=bytearray()
                while len(data)<65536:
                    chunk=conn.recv(min(8192,65536-len(data)))
                    if not chunk:break
                    data+=chunk
                if peer[0]!=remote or data!=expected:
                    raise RuntimeError("TCP64 server received nonidentical payload")
                conn.sendall(data);received.append(len(data))
        except Exception as error:issues.append(str(error))
    stage_barrier(gate,"tcp64k",12)
    worker=threading.Thread(target=serve,daemon=True);worker.start()
    try:
        outbound=payload(local,65507)+bytes(29)
        until=time.monotonic()+5;conn=None
        while time.monotonic()<until:
            try:conn=socket.create_connection((remote,TCP_PORT),timeout=1)
            except (OSError,TimeoutError):time.sleep(.05)
            else:break
        if conn is None:raise RuntimeError("TCP64 real peer connect timeout")
        with conn:
            conn.settimeout(10);conn.sendall(outbound)
            reply=bytearray()
            while len(reply)<65536:
                block=conn.recv(min(8192,65536-len(reply)))
                if not block:break
                reply+=block
            if reply!=outbound:raise RuntimeError("TCP64 genuine echo differs")
        worker.join(timeout=10)
        if worker.is_alive() or issues or received!=[65536]:
            raise RuntimeError("TCP64 server missing "+repr(issues))
        return {"result":"REAL_TCP64K_OS_BYTE_EXACT","written_bytes":65536,"echo_bytes":65536}
    finally:listen.close()

def main():
    if len(sys.argv)!=4:raise ValueError("real local remote and shared-ready")
    local,remote,gate=sys.argv[1:]
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    try:
        s.bind((local,PORT));s.settimeout(.3)
        df0=df_option(s,False)
        print(json.dumps({"phase":"bound","local":local}),flush=True)
        until=time.monotonic()+25
        while not pathlib.Path(gate).is_file():
            if time.monotonic()>until:raise RuntimeError("real peer bind barrier deadline")
            time.sleep(.05)
        failures=[];sizes=[]
        for n in PROBE_SIZES:
            try:
                stage_barrier(gate,"df0-"+str(n),12)
                sends=DF0_SMALL_ATTEMPTS if n==1728 else 1
                for _ in range(sends):
                    if s.sendto(payload(local,n),(remote,PORT))!=n:
                        raise RuntimeError("short native DF0 send")
                    if sends>1:time.sleep(.12)
                expected=payload(remote,n)
                until=time.monotonic()+7;ok=False
                while time.monotonic()<until:
                    try:data,peer=s.recvfrom(65535)
                    except socket.timeout:continue
                    if peer[0]==remote and data==expected:ok=True;break
                    print(json.dumps({"phase":"unexpected_df0_input","expected_size":n,
                         "received_size":len(data),"peer_matches":peer[0]==remote,
                         "payload_matches":data==expected}),flush=True)
                if not ok:raise RuntimeError("native DF0 complete reassembly missing")
                line={"size":n,"result":"DF0_FULL_DATAGRAM_BYTE_EXACT"}
            except Exception as error:
                line={"size":n,"result":"FAIL","reason":str(error)}
                failures.append(line)
            sizes.append(line)
            print(json.dumps({"phase":"DF0",**line}),flush=True)
        df1sizes=[]
        for n in PROBE_SIZES:
            probe=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            try:
                probe.bind((local,0))
                df1=df_option(probe,True)
                code=None
                try:probe.sendto(payload(local,n),(remote,PORT))
                except OSError as error:
                    code=getattr(error,"winerror",None) or error.errno
                line={"size":n,"errno":code,"result":"DF1_EMSGSIZE" if code in (errno.EMSGSIZE,10040) else "FAIL"}
                if line["result"]=="FAIL":failures.append(line)
                df1sizes.append(line)
                print(json.dumps({"phase":"DF1",**line}),flush=True)
            finally:probe.close()
        try:tcp=tcp64k(local,remote,gate)
        except Exception as error:
            tcp={"result":"FAIL","reason":str(error)};failures.append(tcp)
        print(json.dumps({"phase":"TCP64K",**tcp}),flush=True)
        result={"result":"REAL_DF0_REASSEMBLED_DF1_EMSGSIZE" if not failures else "EXTENDED_NATIVE_FAILURE",
          "host_os":os.name,"df0":df0,"df1":df1,"received_bytes":SIZE,
          "df1_errno":df1sizes[0]["errno"],"icmp_type3_code4":"NOT_MEASURED_LOCAL_EMSGSIZE",
          "df0_size_receipts":sizes,"df1_size_receipts":df1sizes,"tcp64k":tcp,
          "source":"REAL_WINDOWS_WINTUN_LINUX_TUN_ORIGINAL_GO_TLS_RUST"}
        print(json.dumps(result,sort_keys=True),flush=True)
        if failures:raise RuntimeError("H990 native extended FAIL "+repr(failures))
    finally:s.close()

if __name__=="__main__":main()
