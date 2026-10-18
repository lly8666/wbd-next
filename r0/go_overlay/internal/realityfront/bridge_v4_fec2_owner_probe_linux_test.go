//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_owner_probe
package realityfront

import (
    "testing"
    "bytes"
    "encoding/binary"
    "fmt"
    "net"
    "os"
    "os/exec"
    "syscall"
    "unsafe"
    "time"
)

// Actual original Go recognized TLS + password + private V4 reply, then
// original Go Detach/Commit Rust; NO synthetic cold constructor authority.
// The extra compile tag makes this test-only scope unavailable in production.
func TestR0V4Fec2ActualGoTLSEpochOwnerGrantScoped(t *testing.T){
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(string(rune('0'+cipher)),func(t *testing.T){
            store,err:=NewV4EpochStore(2)
            if err!=nil{t.Fatal(err)}
            base:=&v4EmbeddedNativeBridge{}
            c0,s0,ce,se:=v4PairWithPrivateBridgeCipher(t,base,store,cipher)
            if ce!=nil||se!=nil||!base.committed||c0==nil||s0==nil{
                t.Fatalf("default V4 owner failed: %v %v",ce,se)
            }
            if base.protectedFeatures!=v4RequiredFeatures ||
                base.fec2ProbeScope(s0.Epoch){
                t.Fatal("default authenticated V4 illegally received FEC2 owner permission")
            }
            if err:=base.stopRelease();err!=nil{t.Fatal(err)}
            if err:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),
                1,s0.Epoch);err!=nil{t.Fatal(err)}
            scoped:=&v4EmbeddedNativeBridge{}
            c,s,ce,se:=v4PairWithPrivateBridgeCipher(t,scoped,store,cipher,true)
            if ce!=nil||se!=nil||c==nil||s==nil||!scoped.committed {
                t.Fatalf("real TLS private FEC2 owner scope not installed: %v %v",ce,se)
            }
            if s.Epoch==s0.Epoch||s.Epoch==[16]byte{} ||
                scoped.handle==0||scoped.protectedFeatures!=7 ||
                scoped.protectedEpoch!=s.Epoch||
                !scoped.fec2ProbeScope(s.Epoch){
                t.Fatal("protected bit2 permission not bound to exact new epoch and generation")
            }
            var bad [16]byte
            bad[0]=s.Epoch[0]^0xff
            if scoped.fec2ProbeScope(bad)||scoped.fec2ProbeScope(s0.Epoch){
                t.Fatal("wrong or retired epoch inherited private FEC2 permission")
            }
            oldHandle:=scoped.handle
            if err:=scoped.stopRelease();err!=nil{t.Fatal(err)}
            if scoped.fec2ProbeScope(s.Epoch){
                t.Fatal("stopped FEC2 scope remained active")
            }
            if _,err:=v4EmbeddedNativeState(oldHandle);err==nil{
                t.Fatal("old generation still registered")
            }
            if err:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),
                1,s.Epoch);err!=nil{t.Fatal(err)}
        })
    }
}

// Explicit privileged network-namespace test. It receives actual M4
// IPv4/TCP packets through an independent ORIGINAL Go raw socket after the
// ORIGINAL Rust generation has encrypted FEC2 SOURCE and REPAIR with PN0/1.
// It does NOT claim that a production client decoded/recovered those bytes.
func TestR0V4Fec2ActualKernelRawSourceRepairAfterProtectedGoTLS(t *testing.T){
    if os.Getenv("WBD_REAL_TUN")!="1" ||
       os.Getenv("WBD_M0_FEC2_KERNEL_TX")!="1" {
        t.Skip("opt-in isolated privileged Linux network namespace only")
    }
    iface,err:=net.InterfaceByName("lo")
    if err!=nil||iface.Index<=0{t.Fatalf("real lo: %v",err)}
    // Original OS TUN owner, not an anonymous pipe/fake app. Root netns
    // isolated by the same original M4 shell driver as Normal/off.
    const tunName="wbdfec2t0"
    tun,e:=os.OpenFile("/dev/net/tun",os.O_RDWR,0)
    if e!=nil{t.Fatal(e)}
    defer tun.Close()
    var ifreq [40]byte
    copy(ifreq[:16],[]byte(tunName))
    binary.LittleEndian.PutUint16(ifreq[16:18],0x1001)
    _,_,errno:=syscall.Syscall(syscall.SYS_IOCTL,tun.Fd(),0x400454ca,
        uintptr(unsafe.Pointer(&ifreq[0])))
    if errno!=0{t.Fatalf("real FEC2 TUN create: %v",errno)}
    for _,args:=range [][]string{{"addr","add","10.241.20.1/24","dev",tunName},
        {"link","set","dev",tunName,"up"}}{
        if out,e:=exec.Command("ip",args...).CombinedOutput();e!=nil{
            t.Fatalf("real FEC2 TUN config %v: %v %s",args,e,out)
        }
    }
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(fmt.Sprintf("suite-%d",cipher),func(t *testing.T){
            store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
            b:=&v4EmbeddedNativeBridge{}
            c,server,ce,se:=v4PairWithPrivateBridgeCipher(t,b,store,cipher,true)
            if ce!=nil||se!=nil||c==nil||server==nil||!b.committed{
                t.Fatalf("real TLS FEC2 bound original Rust owner: %v %v",ce,se)
            }
            defer func(){
                if e:=b.stopRelease();e!=nil{t.Errorf("Stop: %v",e)}
                if e:=store.ReleaseLane("protected-owner",
                    []byte("0123456789abcdef"),1,server.Epoch);e!=nil{
                    t.Errorf("release Go TLS epoch: %v",e)
                }
            }()
            if !b.fec2ProbeScope(server.Epoch){
                t.Fatal("source2/repair3 raw send attempted without Go TLS grant")
            }
            if e=b.attachKernelTun(tun.Fd(),tunName);e!=nil{
                t.Fatalf("original M4 TUN scoped FD attach: %v",e)
            }
            app,e:=net.ListenUDP("udp4",&net.UDPAddr{
                IP:net.IPv4(10,241,20,1),Port:49231,
            })
            if e!=nil{t.Fatal(e)}
            defer app.Close()
            if _,_,_,_,e:=b.fec2ProbeActualM2RxFeedback(11_000_000,1);e==nil{
                t.Fatal("M2 emitted feedback before any authenticated kernel FEC2 DATA")
            }
            peer,e:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_TCP)
            if e!=nil{t.Fatal(e)}
            defer syscall.Close(peer)
            if e:=syscall.Bind(peer,&syscall.SockaddrInet4{
                Addr:b.originalFlow.ClientIP});e!=nil{t.Fatal(e)}
            timeval:=syscall.NsecToTimeval((800*time.Millisecond).Nanoseconds())
            if e:=syscall.SetsockoptTimeval(peer,syscall.SOL_SOCKET,
                syscall.SO_RCVTIMEO,&timeval);e!=nil{t.Fatal(e)}
            pn,seq,wireLen,e:=b.fec2ProbeKernelRawTx(uint32(iface.Index))
            if e!=nil||pn!=[2]uint64{0,1}||
                seq[0]!=b.txBoundary || seq[1]!=seq[0]+wireLen[0] ||
                wireLen[0]<42||wireLen[1]<43||wireLen[0]>1400||wireLen[1]>1400 {
                t.Fatalf("original M1/M4 raw source/repair failed pn=%v seq=%v len=%v err=%v",
                    pn,seq,wireLen,e)
            }
            seen:=[2]bool{}
            var captured [2][]byte
            for attempts:=0;attempts<48 && (!seen[0]||!seen[1]);attempts++{
                buf:=make([]byte,2048)
                n,_,rxErr:=syscall.Recvfrom(peer,buf,0)
                if rxErr!=nil{t.Fatalf("independent raw kernel receive: %v",rxErr)}
                if n<40||buf[0]>>4!=4||buf[9]!=6{continue}
                ihl:=int(buf[0]&15)*4
                if ihl<20||ihl+20>n{continue}
                if !bytes.Equal(buf[12:16],b.originalFlow.ServerIP[:]) ||
                   !bytes.Equal(buf[16:20],b.originalFlow.ClientIP[:])||
                   binary.BigEndian.Uint16(buf[ihl:ihl+2])!=b.originalFlow.ServerPort||
                   binary.BigEndian.Uint16(buf[ihl+2:ihl+4])!=b.originalFlow.ClientPort{
                   continue
                }
                tcpLen:=int(buf[ihl+12]>>4)*4
                if tcpLen<20||ihl+tcpLen>n{continue}
                seq32:=binary.BigEndian.Uint32(buf[ihl+4:ihl+8])
                for i:=range seen{
                    if seq32==seq[i]{
                        if seen[i]{t.Fatalf("duplicate raw sequence %d",seq32)}
                        if n-ihl-tcpLen!=int(wireLen[i]) {
                            t.Fatalf("actual M4 raw encrypted frame length=%d want=%d",
                                n-ihl-tcpLen,wireLen[i])
                        }
                        // Authenticated cipher bytes came from the ORIGINAL
                        // Rust scoped AEAD sender; no plaintext 10/12B FEC2
                        // header may appear on this kernel raw wire.
                        wire:=buf[ihl+tcpLen:n]
                        if bytes.HasPrefix(wire,[]byte("WBDLFRG1"))||
                           bytes.HasPrefix(wire,[]byte{0x46,0x32,0x53,0x00}){
                            t.Fatal("FEC2 source leaked plaintext on raw wire")
                        }
                        captured[i]=append([]byte(nil),wire...)
                        seen[i]=true
                    }
                }
            }
            if !seen[0]||!seen[1]{
                t.Fatalf("missing real kernel raw FEC2 ciphertext source/repair seen=%v",seen)
            }
            // Independent kernel raw peer has captured the exact bytes (not
            // a Rust producer-side slice). Submit actual ciphertext to the
            // ORIGINAL M3 receiver with a different replay PN bitmap,
            // initialized from the original Go verified S2C exporter.
            gotPN,gotKind,recovered,recvErr:=b.fec2ProbeActualPeerConsume(captured[0])
            if recvErr!=nil||gotPN!=0||gotKind!=2||len(recovered)!=0 {
                t.Fatalf("authenticated raw SOURCE had unexpected delivery: pn=%d kind=%d n=%d err=%v",
                    gotPN,gotKind,len(recovered),recvErr)
            }
            // A merely authenticated source fragment is not an IP
            // datagram. The OS app must have NOTHING before recovered e1.
            if err:=app.SetReadDeadline(time.Now().Add(30*time.Millisecond));err!=nil{t.Fatal(err)}
            pre:=make([]byte,160)
            nPre,_,errPre:=app.ReadFromUDP(pre)
            if ne,ok:=errPre.(net.Error);nPre!=0||!ok||!ne.Timeout(){
                t.Fatalf("unauthenticated/pending source leaked UDP app output n=%d err=%v",nPre,errPre)
            }
            // Same valid cipher bytes are a REPLAY, never a second source.
            if _,_,_,recvErr=b.fec2ProbeActualPeerConsume(captured[0]);recvErr==nil{
                t.Fatal("original M3 unique replay PN failed to reject duplicate source")
            }
            corrupted:=append([]byte(nil),captured[1]...)
            corrupted[len(corrupted)/2]^=0x40
            if _,_,_,recvErr=b.fec2ProbeActualPeerConsume(corrupted);recvErr==nil{
                t.Fatal("M3 AEAD admitted tampered independent kernel ciphertext")
            }
            // Tampered repair and duplicate source MUST NOT trigger
            // application delivery or advance M2's authenticated PN ledger.
            if err:=app.SetReadDeadline(time.Now().Add(30*time.Millisecond));err!=nil{t.Fatal(err)}
            nPre,_,errPre=app.ReadFromUDP(pre)
            if ne,ok:=errPre.(net.Error);nPre!=0||!ok||!ne.Timeout(){
                t.Fatalf("tamper/replay leaked UDP app output n=%d err=%v",nPre,errPre)
            }
            gotPN,gotKind,recovered,recvErr=b.fec2ProbeActualPeerConsume(captured[1])
            expectRecovered:=make([]byte,127)
            expectRecovered[0]=0x45
            expectRecovered[8]=64;expectRecovered[9]=17
            binary.BigEndian.PutUint16(expectRecovered[2:4],127)
            binary.BigEndian.PutUint16(expectRecovered[4:6],9102)
            copy(expectRecovered[12:16],net.IPv4(10,241,20,2).To4())
            copy(expectRecovered[16:20],net.IPv4(10,241,20,1).To4())
            binary.BigEndian.PutUint16(expectRecovered[20:22],42001)
            binary.BigEndian.PutUint16(expectRecovered[22:24],49231)
            binary.BigEndian.PutUint16(expectRecovered[24:26],107)
            for i:=28;i<127;i++{
                expectRecovered[i]=byte(((i-28)*7+5)%251)
            }
            binary.BigEndian.PutUint16(expectRecovered[10:12],
                v4RawCheckSum(expectRecovered[:20]))
            if recvErr!=nil||gotPN!=1||gotKind!=3||
               !bytes.Equal(recovered,expectRecovered){
                t.Fatalf("M3 RS16 missing source1 actual kernel parity recovered wrong pn=%d kind=%d len=%d err=%v",
                    gotPN,gotKind,len(recovered),recvErr)
            }
            if _,_,_,recvErr=b.fec2ProbeActualPeerConsume(captured[1]);recvErr==nil{
                t.Fatal("completed M3 parity replay generated another recovery")
            }
            // The result came from actual kernel ciphertext -> M3 AEAD /
            // replay / RS16 and was submitted to ORIGINAL ScopedTunSink.
            // Independent Linux UDP application receipt is mandatory.
            if err:=app.SetReadDeadline(time.Now().Add(2*time.Second));err!=nil{
                t.Fatal(err)
            }
            appPayload:=make([]byte,150)
            n,peerAddr,appErr:=app.ReadFromUDP(appPayload)
            if appErr!=nil||peerAddr==nil||
                !peerAddr.IP.Equal(net.IPv4(10,241,20,2))||
                peerAddr.Port!=42001||n!=99||
                !bytes.Equal(appPayload[:n],expectRecovered[28:]){
                t.Fatalf("real original M4 TUN recovery app UDP failed suite=%d n=%d source=%v err=%v",
                    cipher,n,peerAddr,appErr)
            }
            // M2 original bounded RX feedback is fed ONLY successful
            // original M3 AEAD+PN and typed source/repair; no ACK of ACK
            // or untrusted Go-supplied receipt. One 256-PN page, bits0&1.
            // Check actual driver-outcome lifecycle in the SAME owner:
            // pre-deadline, NotSent, retry, Accepted, one repeat Uncertain.
            if _,_,_,_,e:=b.fec2ProbeActualM2RxFeedback(9_000_000,1);e==nil{
                t.Fatal("M2 report emitted before 10ms steady delay")
            }
            seqM,maxM,baseM,bitsM,e:=b.fec2ProbeActualM2RxFeedback(11_000_000,0)
            if e!=nil||seqM!=0||maxM!=1||baseM!=0||bitsM!=3{
                t.Fatalf("M2 NotSent bits from real AEAD wrong seq=%d max=%d base=%d bitmap=%d err=%v",
                    seqM,maxM,baseM,bitsM,e)
            }
            if _,_,_,_,e:=b.fec2ProbeActualM2RxFeedback(12_000_000,1);e==nil{
                t.Fatal("M2 NotSent allowed too-early retry")
            }
            if _,_,_,_,e:=b.fec2ProbeActualM2RxFeedback(13_000_000,3);e==nil{
                t.Fatal("M2 accepted unsupported fake send status")
            }
            seqM,maxM,baseM,bitsM,e=b.fec2ProbeActualM2RxFeedback(13_000_000,1)
            if e!=nil||seqM!=1||maxM!=1||baseM!=0||bitsM!=3{
                t.Fatalf("M2 Accepted draft incorrect seq=%d max=%d base=%d bitmap=%d err=%v",
                    seqM,maxM,baseM,bitsM,e)
            }
            if _,_,_,_,e:=b.fec2ProbeActualM2RxFeedback(14_000_000,2);e==nil{
                t.Fatal("M2 allowed a repeat before srtt/4")
            }
            seqM,maxM,baseM,bitsM,e=b.fec2ProbeActualM2RxFeedback(15_000_000,2)
            if e!=nil||seqM!=2||maxM!=1||baseM!=0||bitsM!=3{
                t.Fatalf("M2 Uncertain draft wrong seq=%d max=%d base=%d bitmap=%d err=%v",
                    seqM,maxM,baseM,bitsM,e)
            }
            if _,_,_,_,e:=b.fec2ProbeActualM2RxFeedback(17_000_000,1);e==nil{
                t.Fatal("M2 repeated indefinitely after bounded second emission")
            }
            t.Logf("M0_REAL_GO_KERNEL_FEC2_M2_AUTH_RX_FEEDBACK_PASS suite=%d bitmap=03 largest=1 notsent=1 accepted=1 uncertain=1",cipher)
                        t.Logf("M0_REAL_GO_RAW_RUST_FEC2_RS16_M4_TUN_UDP_DELIVERY_PASS suite=%d recovered_ip=127 udp_payload=%d",cipher,n)
            t.Logf("M0_REAL_GO_RAW_RUST_AUTHENTICATED_FEC2_RS16_MISSING_SOURCE_PASS suite=%d e=1 restored=%d source_pn=%d parity_pn=%d",
                cipher,len(recovered),pn[0],pn[1])
            t.Logf("M0_REAL_GO_TLS_ORIGINAL_RUST_FEC2_M4_RAW_TX_PASS suite=%d source_pn=%d repair_pn=%d source_seq=%d repair_seq=%d",
                cipher,pn[0],pn[1],seq[0],seq[1])
            // Stop is a hard terminal for both M2 drafts and recovered
            // kernel ciphertext ingress; stale old handle is not valid.
            if err:=b.stopRelease();err!=nil{t.Fatalf("final Stop/Release: %v",err)}
            if _,_,_,_,e:=b.fec2ProbeActualM2RxFeedback(19_000_000,1);e==nil{
                t.Fatal("M2 RX feedback survived original owner Stop")
            }
            if _,_,_,e:=b.fec2ProbeActualPeerConsume(captured[1]);e==nil{
                t.Fatal("stale owner admitted authenticated repair after Stop")
            }
            t.Logf("M0_REAL_GO_KERNEL_FEC2_NEGATIVE_LIFECYCLE_PASS suite=%d no_partial_udp=1 no_tamper_udp=1 stop_revokes=1",cipher)
        })
    }
}
