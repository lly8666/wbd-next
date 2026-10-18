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

    "github.com/lly8666/wobuzhidao/internal/tlsrecord"
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
            // ACTUAL original Go TLS credential-checked C2S key seals
            // authenticated kind1. Real AF_INET/IP_HDRINCL kernel packets
            // cross M4 raw RX into the ORIGINAL Rust scoped M3 C2S opener
            // and M2 typed ingress, releasing only previously confirmed
            // ORIGINAL M1 FrozenRecord sender loans. 52-byte typed receipt
            // grammar remains opt-in fixture, not product peer wire policy.
            outstanding,e:=b.fec2ProbeShadowOutstanding()
            if e!=nil||outstanding!=2 {
                t.Fatalf("raw kernel confirmed sender shadows=%d err=%v",outstanding,e)
            }
            if e=b.attachRawRx(uint32(iface.Index));e!=nil{
                t.Fatalf("original M4 reverse raw RX: %v",e)
            }
            origCold,e:=c.ColdSnapshot()
            if e!=nil{t.Fatal(e)}
            _,c2sLimit:=origCold.RecordLimits()
            reverseSealer,e:=tlsrecord.NewSealerForCipher(
                origCold.DirectionKeys().C2S,int(c2sLimit),cipher)
            if e!=nil{t.Fatal(e)}
            receipt:=make([]byte,52)
            binary.BigEndian.PutUint32(receipt[0:4],seqM)
            binary.BigEndian.PutUint64(receipt[4:12],maxM)
            binary.BigEndian.PutUint64(receipt[12:20],baseM)
            // Test-only SELECTIVE missing evidence: the peer-side Go
            // fixture deliberately reports only source PN0 positive,
            // leaving parity PN1 missing. This is NOT a proven packet
            // drop: the separate RS16 test already consumed both records.
            receipt[20]=1
            if seqM!=2||maxM!=1||baseM!=0||bitsM!=3{
                t.Fatal("M2 actual authenticated draft source changed")
            }
            encryptedControl,controlPN,e:=reverseSealer.SealHealth(receipt)
            if e!=nil||controlPN!=0{
                t.Fatalf("original Go C2S control seal pn=%d err=%v",controlPN,e)
            }
            rawControlFD,e:=syscall.Socket(syscall.AF_INET,
                syscall.SOCK_RAW,syscall.IPPROTO_RAW)
            if e!=nil{t.Fatal(e)}
            defer syscall.Close(rawControlFD)
            if e=syscall.SetsockoptInt(rawControlFD,syscall.IPPROTO_IP,
                syscall.IP_HDRINCL,1);e!=nil{t.Fatal(e)}
            sendControl:=func(record []byte){
                rawPacket:=v4RawC2STestPacket(record,b.rxBoundary,b.originalFlow)
                if sendErr:=syscall.Sendto(rawControlFD,rawPacket,0,
                    &syscall.SockaddrInet4{Addr:b.originalFlow.ServerIP});
                    sendErr!=nil{t.Fatalf("actual C2S control raw: %v",sendErr)}
            }
            badCipher:=append([]byte(nil),encryptedControl...)
            badCipher[len(badCipher)/2]^=0x40
            sendControl(badCipher)
            if n,left,err:=b.fec2ProbeReverseRawReceipt();
                err==nil||n!=0||left!=0{
                t.Fatalf("tampered real reverse kind1 released shadow n=%d left=%d err=%v",n,left,err)
            }
            if n,e:=b.fec2ProbeShadowOutstanding();e!=nil||n!=2{
                t.Fatal("bad AEAD mutated original sender frozen loans")
            }
            sendControl(encryptedControl)
            retired,left,e:=b.fec2ProbeReverseRawReceipt()
            if e!=nil||retired!=1||left!=1{
                t.Fatalf("selective M2 receipt should retire only PN0 n=%d remaining=%d err=%v",
                    retired,left,e)
            }
            if n,e:=b.fec2ProbeShadowOutstanding();e!=nil||n!=1{
                t.Fatal("M2 missing bitmap prematurely retired original parity PN1")
            }
            // PTO and original global M2 scoped grant reserve exactly one
            // ORIGINAL FrozenRecord. Actual M4 send_one copies the SAME
            // PN1/Seq/ciphertext: no new seal or fresh TX queue. Driver
            // accepted prefix does not mean peer received anything.
            repairPN,repairSeq,repairWire,charged,e:=b.fec2ProbeRealFrozenRepair()
            if e!=nil||repairPN!=pn[1]||repairSeq!=seq[1]||
                repairWire!=wireLen[1]||charged<=uint64(repairWire){
                t.Fatalf("same M1 frozen retransmission mismatch PN=%d Seq=%d wire=%d charge=%d err=%v",
                    repairPN,repairSeq,repairWire,charged,e)
            }
            repairSeen:=false
            for attempts:=0;attempts<48;attempts++{
                buf:=make([]byte,2048)
                n,_,rxErr:=syscall.Recvfrom(peer,buf,0)
                if rxErr==syscall.EINTR||rxErr==syscall.EAGAIN{continue}
                if rxErr!=nil{t.Fatalf("original Go real M4 repair capture err=%v",rxErr)}
                if n<40||buf[0]>>4!=4||buf[9]!=6{continue}
                ihl:=int(buf[0]&15)*4
                if ihl<20||ihl+20>n{continue}
                if !bytes.Equal(buf[12:16],b.originalFlow.ServerIP[:])||
                   !bytes.Equal(buf[16:20],b.originalFlow.ClientIP[:])||
                   binary.BigEndian.Uint16(buf[ihl:ihl+2])!=b.originalFlow.ServerPort||
                   binary.BigEndian.Uint16(buf[ihl+2:ihl+4])!=b.originalFlow.ClientPort{
                    continue
                }
                tcpLen:=int(buf[ihl+12]>>4)*4
                if tcpLen<20||ihl+tcpLen>n{continue}
                if binary.BigEndian.Uint32(buf[ihl+4:ihl+8])!=repairSeq{continue}
                if uint32(n-ihl-tcpLen)!=repairWire||
                    !bytes.Equal(buf[ihl+tcpLen:n],captured[1]){
                    t.Fatalf("real kernel repair mutated original M3 ciphertext or PN/Seq")
                }
                repairSeen=true
                break
            }
            if !repairSeen{t.Fatal("real M4 same-FrozenRecord repair not observed by Go raw peer")}
            // Replay of the first authenticated negative record does not
            // trigger a second candidate or quota debit.
            sendControl(encryptedControl)
            if _,_,e:=b.fec2ProbeReverseRawReceipt();e==nil{
                t.Fatal("real reverse replay PN granted another repair")
            }
            if _,_,_,_,e:=b.fec2ProbeRealFrozenRepair();e==nil{
                t.Fatal("same evidence produced an immediate second repair")
            }
            // Fresh authenticated positive PN1 from the independent Go
            // TLS direction retires only the still retained repaired handle.
            positiveReceipt:=append([]byte(nil),receipt...)
            binary.BigEndian.PutUint32(positiveReceipt[0:4],seqM+1)
            positiveReceipt[20]=bitsM
            positiveWire,positivePN,e:=reverseSealer.SealHealth(positiveReceipt)
            if e!=nil||positivePN!=1{t.Fatalf("positive control PN err=%v pn=%d",e,positivePN)}
            sendControl(positiveWire)
            retired,left,e=b.fec2ProbeReverseRawReceipt()
            if e!=nil||retired!=1||left!=0{
                t.Fatalf("late positive authenticated PN1 missing release n=%d left=%d err=%v",
                    retired,left,e)
            }
            if n,e:=b.fec2ProbeShadowOutstanding();e!=nil||n!=0{
                t.Fatal("late authenticated receipt did not retire exact original frozen handle")
            }
            invalidReceipt:=append([]byte(nil),positiveReceipt...)
            invalidReceipt[20]=0x80 // PN7 outside pinned data scope 0..1
            badScopeWire,badScopePN,e:=reverseSealer.SealHealth(invalidReceipt)
            if e!=nil||badScopePN!=2{t.Fatalf("control PN allocation: %v %d",e,badScopePN)}
            sendControl(badScopeWire)
            if _,_,e:=b.fec2ProbeReverseRawReceipt();e==nil{
                t.Fatal("authenticated out-of-scope bitmap admitted")
            }
            if n,e:=b.fec2ProbeShadowOutstanding();e!=nil||n!=0{
                t.Fatal("out-of-scope receipt changed original frozen sender state")
            }
            t.Logf("M0_REAL_GO_M2_SAME_FROZEN_RAW_REPAIR_PREFIX_PASS suite=%d pn=1 same_seq=1 byte_identical=1 global_grant=1 driver_accepted=1 late_auth_receipt=1 synthetic_negative=1",cipher)
            t.Logf("M0_REAL_GO_TLS_M4_RAW_REVERSE_M3_AEAD_PN_M2_FROZEN_RECEIPT_PASS suite=%d retired=2 original_pn=0,1 tamper=deny replay=deny bitmap_scope=deny",cipher)
            // Stop is a hard terminal for both M2 drafts and recovered
            // kernel ciphertext ingress; stale old handle is not valid.
            if err:=b.stopRelease();err!=nil{t.Fatalf("final Stop/Release: %v",err)}
            if _,e:=b.fec2ProbeShadowOutstanding();e==nil{
                t.Fatal("stale M2 sender shadow survived original owner Stop")
            }
            if _,_,e:=b.fec2ProbeReverseRawReceipt();e==nil{
                t.Fatal("stale original Rust M3 reverse ingress survived Stop")
            }
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
