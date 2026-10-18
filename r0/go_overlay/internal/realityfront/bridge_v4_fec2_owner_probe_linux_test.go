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

// Three simultaneously alive ORIGINAL Go credential-checked TLS owners.
// A single Rust process-global 64KiB repair cap must NOT be multiplied
// by each valid connection. The two earlier grants stay live while the
// third is denied; retiring one exact owner releases ONLY its UNUSED grant.
func TestR0V4Fec2ActualGoTLSProcessSharedRepairQuota(t *testing.T){
    type live struct{
        b *v4EmbeddedNativeBridge
        store *V4EpochStore
        epoch [16]byte
    }
    var owners [3]live
    for i:=range owners{
        store,e:=NewV4EpochStore(1)
        if e!=nil{t.Fatal(e)}
        b:=&v4EmbeddedNativeBridge{}
        _,server,ce,se:=v4PairWithPrivateBridgeCipher(
            t,b,store,CipherChaCha,true)
        if ce!=nil||se!=nil||server==nil||!b.committed||
            !b.fec2ProbeScope(server.Epoch){
            t.Fatalf("original Go protected TLS owner %d failed ce=%v se=%v",i,ce,se)
        }
        owners[i]=live{b:b,store:store,epoch:server.Epoch}
    }
    defer func(){
        for i:=range owners {
            o:=owners[i]
            if o.b.handle!=0{
                if e:=o.b.stopRelease();e!=nil{t.Errorf("owner %d stop %v",i,e)}
            }
            if e:=o.store.ReleaseLane("protected-owner",
                []byte("0123456789abcdef"),1,o.epoch);e!=nil {
                t.Errorf("owner %d epoch release: %v",i,e)
            }
        }
    }()
    count,held,cap,e:=owners[0].b.fec2ProbeProcessQuotaSnapshot()
    if e!=nil||count!=3||held!=0||cap!=65_536 {
        t.Fatalf("three separate verified owners not process registered count=%d held=%d cap=%d err=%v",count,held,cap,e)
    }
    if e=owners[0].b.fec2ProbeProcessQuotaHold(32_768);e!=nil{
        t.Fatalf("first original owner grant: %v",e)
    }
    if e=owners[1].b.fec2ProbeProcessQuotaHold(32_768);e!=nil{
        t.Fatalf("second original owner grant: %v",e)
    }
    count,held,cap,e=owners[2].b.fec2ProbeProcessQuotaSnapshot()
    if e!=nil||count!=3||held!=cap||cap!=65_536 {
        t.Fatalf("held grant cap multiplied count=%d held=%d cap=%d err=%v",count,held,cap,e)
    }
    if e=owners[2].b.fec2ProbeProcessQuotaHold(1);e==nil{
        t.Fatal("third valid original Go TLS owner bypassed process cap")
    }
    if e=owners[0].b.stopRelease();e!=nil{
        t.Fatalf("first exact original owner Stop must revoke unused grant: %v",e)
    }
    if e=owners[0].b.fec2ProbeProcessQuotaHold(1);e==nil{
        t.Fatal("stopped original owner could mint process grants")
    }
    count,held,cap,e=owners[1].b.fec2ProbeProcessQuotaSnapshot()
    if e!=nil||count!=2||held!=32_768||cap!=65_536{
        t.Fatalf("Stop leaked grants/other owner count=%d held=%d cap=%d err=%v",count,held,cap,e)
    }
    if e=owners[2].b.fec2ProbeProcessQuotaHold(32_768);e!=nil{
        t.Fatalf("after Stop unspent process capacity not released: %v",e)
    }
    if e=owners[1].b.fec2ProbeProcessQuotaHold(1);e==nil{
        t.Fatal("second owner minted a duplicate grant while live")
    }
    t.Log("M0_ORIGINAL_GO_TLS_THREE_OWNER_PROCESS_GLOBAL_M2_CAP_PASS registered=3 two_32KiB=held third=denied stop_unused=reclaimed independent_owner=preserved")
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
        for _,mode:=range []string{"single","mixed-prefix","kernel-multimsg"}{
        t.Run(fmt.Sprintf("suite-%d-%s",cipher,mode),func(t *testing.T){
            store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
            b:=&v4EmbeddedNativeBridge{}
            var policyState FecV2State
            // Real ORIGINAL Go cold policy drives original Rust M1/M3
            // parity, not just an independent table test. Different modes
            // require different on-wire e1 plan for k2 (Mild => r1).
            if mode!="single"{
                chosen,revision:=FecV2High,uint64(5)
                policyMode:=FecV2Auto
                var start *FecV2Profile
                if mode=="kernel-multimsg"{
                    chosen,revision=FecV2Mild,9
                    policyMode=FecV2Fixed
                }else{
                    // M4 original Go AUTO startup selects High. This is
                    // a policy-applied REAL TLS kernel path, not continuous
                    // 2s auto sampling or production GUI/CLI.
                    start=&chosen
                }
                var policyErr error
                policyState,policyErr=b.fec2ProbeChoosePolicy(FecV2Config{
                    Client:"protected-owner",Direction:FecV2S2C,
                    Transport:FecV2Normal,Mode:policyMode,
                    Profile:chosen,AutoPolicy:FecV2Conservative,
                    StartProfile:start,ConfigRevision:revision,
                })
                if policyErr!=nil{t.Fatalf("Go policy pre-TLS mode=%s: %v",mode,policyErr)}
            }
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
            if mode!="single"{
                effective,policyErr:=b.fec2ProbeAppliedPolicy(policyState)
                if policyErr!=nil||effective.AppliedRevision!=policyState.RequestedRevision||
                   effective.AppliedProfile!=policyState.Desired||effective.AppliedOff{
                    t.Fatalf("Go policy not really applied by original authenticated Rust owner mode=%s effective=%+v err=%v",
                        mode,effective,policyErr)
                }
                stale,ok,policyErr:=FecV2Apply(effective,FecV2Ack{
                    Client:effective.Client,Direction:effective.Direction,
                    Revision:effective.RequestedRevision-1,
                    Profile:effective.Desired,Applied:true,
                })
                if policyErr!=nil||ok||stale.AppliedRevision!=effective.AppliedRevision{
                    t.Fatal("stale Go policy application receipt rewrote effective state")
                }
                policyState=effective // retain the ORIGINAL Go applied ACK before next 2s auto tick
                t.Logf("M0_REAL_GO_FEC2_POLICY_APPLIED_ORIGINAL_RUST_OWNER_PASS suite=%d mode=%s policy=%s profile=%d revision=%d applied=1 stale_ack=deny",
                    cipher,mode,policyState.Mode,effective.AppliedProfile,effective.AppliedRevision)
            }
            // Same ORIGINAL protected TLS epoch/generation: two mature
            // Go AUTO observation windows from the existing policy module
            // request Maximum/revision6, but MUST NOT mark it applied yet.
            // The next original M1 new-block/M4 real kernel copy commits.
            if mode=="mixed-prefix"{
                cfg:=FecV2Config{
                    Client:"protected-owner",Direction:FecV2S2C,
                    Transport:FecV2Normal,Mode:FecV2Auto,
                    AutoPolicy:FecV2Conservative,ConfigRevision:5,
                }
                for _,sec:=range []int{2,4}{
                    at:=time.Duration(sec)*time.Second
                    quality:=FecV2Snapshot{
                        Client:"protected-owner",Direction:FecV2S2C,
                        At:at,Validity:FecV2Valid,
                        Fast:FecV2Window{FirstSent:1024,Observed:1024,Missing:310},
                        Slow:FecV2Window{FirstSent:6000,Observed:6000,Missing:1800},
                    }
                    quality.ActualK[15]=375
                    newState,intent,tickErr:=b.fec2ProbeStageAutoTick(
                        cfg,policyState,quality,at)
                    if tickErr!=nil||intent.Send!=(sec==4){
                        t.Fatalf("original Go matured AUTO policy tick sec=%d state=%+v intent=%+v err=%v",
                            sec,newState,intent,tickErr)
                    }
                    policyState=newState
                }
                if policyState.Desired!=FecV2Maximum ||
                    policyState.RequestedRevision!=6||
                    policyState.AppliedRevision!=5{
                    t.Fatalf("Go auto2s did not stage new profile without early applied ack: %+v",policyState)
                }
                if _,e:=b.fec2ProbeAppliedPolicy(policyState);e==nil{
                    t.Fatal("pending Go AUTO revision was falsely acknowledged by Rust before new M1 block")
                }
                t.Logf("M0_GO_FEC2_AUTO_PENDING_BEFORE_NEW_BLOCK_PASS suite=%d requested=6 applied=5 two_real_policy_windows=1",cipher)
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
            if mode=="mixed-prefix"{
                applied,ackErr:=b.fec2ProbeAppliedPolicy(policyState)
                if ackErr!=nil||applied.AppliedRevision!=6||
                    applied.AppliedProfile!=FecV2Maximum{
                    t.Fatalf("new original M1 block/M4 kernel copy failed exact pending Rust apply ack state=%+v err=%v",
                        applied,ackErr)
                }
                if _,e:=b.fec2ProbeAppliedPolicy(FecV2State{
                    Initialized:true,Client:"protected-owner",
                    Direction:FecV2S2C,RequestedRevision:5,
                    Desired:FecV2High,
                });e==nil{
                    t.Fatal("old same-epoch Go AUTO applied readback repainted revision6")
                }
                t.Logf("M0_GO_FEC2_AUTO_TWO_WINDOWS_NEXT_M1_M4_BLOCK_APPLIED_PASS suite=%d initial=high5 requested=maximum6 applied=maximum6 old_ack=deny",cipher)
                policyState=applied
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
            if mode!="single"{receipt[20]=0}
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
            expectedRetired,expectedLeft:=uint32(1),uint32(1)
            if mode!="single"{expectedRetired,expectedLeft=0,2}
            if e!=nil||retired!=expectedRetired||left!=expectedLeft{
                t.Fatalf("selective M2 receipt mode=%s n=%d remaining=%d err=%v",
                    mode,retired,left,e)
            }
            if n,e:=b.fec2ProbeShadowOutstanding();e!=nil||n!=expectedLeft{
                t.Fatalf("M2 missing PN bitmap changed original shadows mode=%s n=%d err=%v",mode,n,e)
            }
            // PTO and original global M2 scoped grant reserve exactly one
            // ORIGINAL FrozenRecord. Actual M4 send_one copies the SAME
            // PN1/Seq/ciphertext: no new seal or fresh TX queue. Driver
            // accepted prefix does not mean peer received anything.
            expectedRepaired:=1
            var repairPN uint64
            var repairSeq,repairWire uint32
            var charged uint64
            if mode=="mixed-prefix"{
                expectedRepaired=0
                var neverAttempted uint64
                repairPN,repairSeq,repairWire,charged,neverAttempted,e=
                    b.fec2ProbeRealFrozenPrefixTwo()
                if e!=nil||neverAttempted<=uint64(wireLen[1]){
                    t.Fatalf("positive no-syscall slot must be charged then refunded bytes=%d err=%v",neverAttempted,e)
                }
            }else if mode=="kernel-multimsg"{
                expectedRepaired=0
                var secondOuter uint64
                repairPN,repairSeq,repairWire,charged,secondOuter,e=
                    b.fec2ProbeRealKernelMultimsgTwo()
                if e!=nil||secondOuter<=uint64(wireLen[1])||
                    charged!=uint64(40+wireLen[0])+uint64(40+wireLen[1]){
                    t.Fatalf("one genuine M4 sendmmsg must kernel-accept two original M1 frozen packets charge=%d secondOuter=%d err=%v",charged,secondOuter,e)
                }
            }else{
                repairPN,repairSeq,repairWire,charged,e=b.fec2ProbeRealFrozenRepair()
            }
            if e!=nil||repairPN!=pn[expectedRepaired]||
                repairSeq!=seq[expectedRepaired]||
                repairWire!=wireLen[expectedRepaired]||
                charged<=uint64(repairWire){
                t.Fatalf("same M1 frozen repair mode=%s PN=%d Seq=%d wire=%d charge=%d err=%v",
                    mode,repairPN,repairSeq,repairWire,charged,e)
            }
            repairedSeen:=[2]bool{}
            for attempts:=0;attempts<64;attempts++{
                buf:=make([]byte,2048)
                n,_,rxErr:=syscall.Recvfrom(peer,buf,0)
                if rxErr==syscall.EINTR||rxErr==syscall.EAGAIN{continue}
                if rxErr!=nil{t.Fatalf("original Go actual M4 repair kernel capture err=%v",rxErr)}
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
                gotSeq:=binary.BigEndian.Uint32(buf[ihl+4:ihl+8])
                for ix:=0;ix<2;ix++{
                    if gotSeq!=seq[ix]||repairedSeen[ix]{continue}
                    if mode!="kernel-multimsg"&&ix!=expectedRepaired{continue}
                    if uint32(n-ihl-tcpLen)!=wireLen[ix]||
                        !bytes.Equal(buf[ihl+tcpLen:n],captured[ix]){
                        t.Fatalf("original M4 repaired frozen ciphertext changed in slot=%d mode=%s",ix,mode)
                    }
                    repairedSeen[ix]=true
                }
                if mode=="kernel-multimsg"{
                    if repairedSeen[0]&&repairedSeen[1]{break}
                }else if repairedSeen[expectedRepaired]{break}
            }
            if mode=="kernel-multimsg"{
                if !repairedSeen[0]||!repairedSeen[1]{
                    t.Fatalf("one true original M4 sendmmsg did not kernel-deliver BOTH originals seen=%v",repairedSeen)
                }
            }else if !repairedSeen[expectedRepaired]{
                t.Fatal("real M4 same-FrozenRecord repair not observed by Go raw peer")
            }
            // Replay of the first authenticated negative record does not
            // trigger a second candidate or quota debit.
            sendControl(encryptedControl)
            if _,_,e:=b.fec2ProbeReverseRawReceipt();e==nil{
                t.Fatal("real reverse replay PN granted another repair")
            }
            if mode=="mixed-prefix"{
                if _,_,_,_,_,e:=b.fec2ProbeRealFrozenPrefixTwo();e==nil{
                    t.Fatal("same evidence produced a second mixed-prefix reservation")
                }
            }else if mode=="kernel-multimsg"{
                if _,_,_,_,_,e:=b.fec2ProbeRealKernelMultimsgTwo();e==nil{
                    t.Fatal("same authenticated negative evidence produced second kernel sendmmsg")
                }
            }else{
                if _,_,_,_,e:=b.fec2ProbeRealFrozenRepair();e==nil{
                    t.Fatal("same evidence produced an immediate second repair")
                }
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
            if e!=nil||retired!=expectedLeft||left!=0{
                t.Fatalf("late positive authenticated missing release mode=%s n=%d left=%d err=%v",
                    mode,retired,left,e)
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
            if mode=="mixed-prefix"{
                t.Logf("M0_REAL_GO_M2_MIXED_TWO_FROZEN_DRIVER_PREFIX_PASS suite=%d actual_kernel_first=1 proven_no_syscall_second=1 refunded_unused=1 later_auth_releases_two=1 same_pn_seq_cipher=1",cipher)
            }else if mode=="kernel-multimsg"{
                t.Logf("M0_REAL_GO_M4_NATIVE_SENDMMSG_TWO_ORIGINAL_FROZEN_M2_PREFIX_PASS suite=%d real_kernel_messages=2 same_pn_seq_cipher=2 original_m2_reserved=2 charged=2 late_auth_releases=2 no_reseal=1",cipher)
            }else{
                t.Logf("M0_REAL_GO_M2_SAME_FROZEN_RAW_REPAIR_PREFIX_PASS suite=%d pn=1 same_seq=1 byte_identical=1 global_grant=1 driver_accepted=1 late_auth_receipt=1 synthetic_negative=1",cipher)
            }
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
}
