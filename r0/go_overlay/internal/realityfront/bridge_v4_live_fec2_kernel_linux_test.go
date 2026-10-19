//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_owner_probe
package realityfront
import (
    "bytes"
    "encoding/binary"
    "net"
    "os"
    "os/exec"
    "syscall"
    "testing"
    "time"
    "unsafe"
)

// Original protected Go TLS feature7, original Go TUN application,
// original Rust *background* owner M1 FEC2 TX / M3 record / M4 raw kernel
// and an independent authenticated original exporter-key CLIENT RX.
// This is not a real production client or AUTO/GUI qualification.
func TestR0V4Fec2ContinuousOriginalGoKernelSourceAndParity(t *testing.T){
    if os.Getenv("WBD_REAL_TUN")!="1"||
       os.Getenv("WBD_M0_FEC2_CONTINUOUS")!="1"{
        t.Skip("requires one isolated M0 original Linux netns")
    }
    const tunName="wbdfeccont0"
    dev,err:=os.OpenFile("/dev/net/tun",os.O_RDWR,0)
    if err!=nil{t.Fatal(err)}
    defer dev.Close()
    var req [40]byte
    copy(req[:16],[]byte(tunName))
    binary.LittleEndian.PutUint16(req[16:18],0x1001)
    _,_,errno:=syscall.Syscall(syscall.SYS_IOCTL,dev.Fd(),0x400454ca,
        uintptr(unsafe.Pointer(&req[0])))
    if errno!=0{t.Fatalf("real continuous FEC TUN ioctl: %v",errno)}
    for _,args:=range [][]string{
        {"addr","add","10.241.24.1/24","dev",tunName},
        {"link","set","dev",tunName,"up"},
    }{
        if output,e:=exec.Command("ip",args...).CombinedOutput();e!=nil{
            t.Fatalf("TUN %v %v %s",args,e,output)
        }
    }
    lo,err:=net.InterfaceByName("lo")
    if err!=nil{t.Fatal(err)}
    src:=net.IPv4(10,241,24,1)
    dst:=net.IPv4(10,241,24,2)
    app,err:=net.ListenUDP("udp4",&net.UDPAddr{IP:src,Port:0})
    if err!=nil{t.Fatal(err)}
    defer app.Close()
    store,err:=NewV4EpochStore(1)
    if err!=nil{t.Fatal(err)}
    b:=&v4EmbeddedNativeBridge{}
    client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,b,store,CipherChaCha,true)
    if ce!=nil||se!=nil||server==nil||!b.committed||
        b.protectedFeatures!=(v4RequiredFeatures|v4FeatureFEC2){
        t.Fatalf("Go protected feature7 TLS credentials/epoch missing: %v %v",ce,se)
    }
    t.Cleanup(func(){
        if b.handle!=0{
            if e:=b.stopRelease();e!=nil{t.Errorf("original Rust Stop: %v",e)}
        }
        if e:=store.ReleaseLane("protected-owner",
            []byte("0123456789abcdef"),1,server.Epoch);e!=nil{
            t.Errorf("original Go TLS lane release: %v",e)
        }
    })
    cfg:=FecV2Config{Client:"protected-owner",Direction:FecV2S2C,
        Transport:FecV2Normal,Mode:FecV2Fixed,Profile:FecV2Mild,
        ConfigRevision:4}
    pending,ack,e:=b.stageOriginalFixedPending(cfg,FecV2State{},server.Epoch)
    if e!=nil||ack.Applied||ack.Rejected||pending.RequestedRevision!=4{
        t.Fatalf("original Go Fixed TLS stage %+v %+v %v",pending,ack,e)
    }
    if e:=b.attachRawRx(uint32(lo.Index));e!=nil{t.Fatal(e)}
    if e:=b.attachKernelTun(dev.Fd(),tunName);e!=nil{t.Fatal(e)}
    peer,err:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_TCP)
    if err!=nil{t.Fatal(err)}
    defer syscall.Close(peer)
    if err:=syscall.Bind(peer,&syscall.SockaddrInet4{Addr:b.originalFlow.ClientIP});err!=nil{
        t.Fatal(err)
    }
    wait:=syscall.NsecToTimeval((100*time.Millisecond).Nanoseconds())
    if err:=syscall.SetsockoptTimeval(peer,syscall.SOL_SOCKET,syscall.SO_RCVTIMEO,&wait);err!=nil{
        t.Fatal(err)
    }
    if err:=b.startRustOwnerLoop(uint32(lo.Index));err!=nil{t.Fatal(err)}
    const packets=4
    expected:=map[string]bool{}
    for i:=0;i<packets;i++{
        data:=bytes.Repeat([]byte{byte(71+i)},64)
        expected[string(data)]=true
        if n,e:=app.WriteToUDP(data,&net.UDPAddr{IP:dst,Port:42125});
            e!=nil||n!=len(data){t.Fatalf("real Go UDP into original TUN n=%d %v",n,e)}
        // One sparse block each, with a real due parity quantum. No
        // synthetic M1 producer call; these bytes originated in Go UDP.
        time.Sleep(18*time.Millisecond)
    }
    // After original source TX has entered the real kernel, bring up a
    // separate CLIENT TUN. This must NOT short-circuit the initial
    // server UDP→TUN ingress: client IP becomes local only now.
    const clientName="wbdfeccli0"
    clientDev,e:=os.OpenFile("/dev/net/tun",os.O_RDWR,0)
    if e!=nil{t.Fatal(e)}
    defer clientDev.Close()
    var clientReq [40]byte
    copy(clientReq[:16],[]byte(clientName))
    binary.LittleEndian.PutUint16(clientReq[16:18],0x1001)
    _,_,clientErrno:=syscall.Syscall(syscall.SYS_IOCTL,clientDev.Fd(),
        0x400454ca,uintptr(unsafe.Pointer(&clientReq[0])))
    if clientErrno!=0{t.Fatalf("real client TUN ioctl: %v",clientErrno)}
    for _,args:=range [][]string{
        {"addr","add","10.241.24.2/32","dev",clientName},
        {"link","set","dev",clientName,"up"},
    }{
        if output,e:=exec.Command("ip",args...).CombinedOutput();e!=nil{
            t.Fatalf("real client TUN setup %v %v %s",args,e,output)
        }
    }
    // This deliberate SAME-netns test has server source IP 10.241.24.1
    // assigned locally on its original TUN. Linux would reject an inbound
    // CLIENT-TUN packet with that *other local* source as a martian before
    // UDP demux. Production client is a different netns/host and never
    // needs accept_local. Only relax isolated test namespace filtering.
    for file,value:=range map[string]string{
        "/proc/sys/net/ipv4/conf/all/rp_filter":"0\n",
        "/proc/sys/net/ipv4/conf/"+clientName+"/rp_filter":"0\n",
        "/proc/sys/net/ipv4/conf/"+clientName+"/accept_local":"1\n",
    }{
        if e:=os.WriteFile(file,[]byte(value),0600);e!=nil{
            t.Fatalf("isolated client test netns martian/rp_filter setup %s: %v",file,e)
        }
    }
    clientApp,e:=net.ListenUDP("udp4",&net.UDPAddr{IP:dst,Port:42125})
    if e!=nil{t.Fatal(e)}
    defer clientApp.Close()
    if client==nil{t.Fatal("original TLS V4 client missing")}
    releaseClient,e:=client.prepareFec2ReleaseClientTun(clientDev.Fd(),clientName)
    if e!=nil{t.Fatalf("original Go verified release client install: %v",e)}
    defer func(){
        if e:=releaseClient.stop();e!=nil{
            t.Errorf("original Rust release client Stop: %v",e)
        }
    }()
    originalDelivered:=0
    paritySilent:=0
    recoveredFirst:=0
    recordsSeen:=0
    droppedOneOriginalSource:=false
    deadline:=time.Now().Add(4*time.Second)
    for time.Now().Before(deadline) {
        buf:=make([]byte,2048)
        n,_,e:=syscall.Recvfrom(peer,buf,0)
        if e!=nil{continue}
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
        if tcpLen<20||ihl+tcpLen>n||buf[ihl+13]&0x08==0||
            n-ihl-tcpLen<31{continue}
        wire:=buf[ihl+tcpLen:n]
        if !droppedOneOriginalSource{
            // The client-side simulated network boundary loses the first
            // ACTUAL raw-kernel source ciphertext. No native M3 opener
            // sees this PN; later real parity MUST reconstruct that
            // original IPv4 application packet, not merely source-copy it.
            droppedOneOriginalSource=true
            continue
        }
        result,e:=releaseClient.consumeAuthenticatedKernelRecord(wire)
        if e!=nil{
            t.Fatalf("original TLS client release M3 AEAD FEC2 peer: %v",e)
        }
        recordsSeen++
        originalDelivered+=int(result.KernelDelivered)
        recoveredFirst+=int(result.Recovered)
        if result.KernelDelivered==0{paritySilent++}
        if originalDelivered==packets && recoveredFirst>=1 && recordsSeen>=6{
            break
        }
    }
    if !droppedOneOriginalSource||recordsSeen<6||originalDelivered!=packets||
        recoveredFirst<1||paritySilent<2{
        t.Fatalf("real original Go release client FEC2 data incomplete copies=%d seen=%d parity=%d recovered=%d",
            originalDelivered,recordsSeen,paritySilent,recoveredFirst)
    }
    // Every first-delivery candidate is sent through the original
    // scoped Rust M4 device writer into the real client TUN. Check an
    // independent Linux UDP application received four exactly-once,
    // including the intentionally dropped source's RS16 recovery.
    clientDelivered:=map[string]bool{}
    for i:=0;i<packets;i++{
        if e:=clientApp.SetReadDeadline(time.Now().Add(time.Second));e!=nil{t.Fatal(e)}
        output:=make([]byte,256)
        n,from,e:=clientApp.ReadFromUDP(output)
        if e!=nil||from==nil||!from.IP.Equal(src)||n!=64{
            t.Fatalf("real client TUN UDP delivery i=%d n=%d from=%v err=%v",i,n,from,e)
        }
        got:=string(output[:n])
        if !expected[got]||clientDelivered[got]{
            t.Fatalf("client native TUN app unauthorized/duplicate i=%d",i)
        }
        clientDelivered[got]=true
    }
    if len(clientDelivered)!=packets{t.Fatalf("client TUN app only received %d",len(clientDelivered))}
    // The CLIENT's independently bound C2S AEAD sealer derived a
    // WBC4/M2 receipt only from original S2C authenticated+unique PNs.
    // Send THIS exact encrypted record across actual Linux IP_HDRINCL,
    // and let original Rust M4 receive it on its single C2S opener.
    time.Sleep(12*time.Millisecond)
    draft,e:=releaseClient.feedbackDue()
    if e!=nil||len(draft.Ciphertext)<31{
        t.Fatalf("client authenticated M2 C2S draft absent: %d %v",
            len(draft.Ciphertext),e)
    }
    rawFeedback,e:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_RAW)
    if e!=nil{t.Fatal(e)}
    defer syscall.Close(rawFeedback)
    if e:=syscall.SetsockoptInt(rawFeedback,syscall.IPPROTO_IP,
        syscall.IP_HDRINCL,1);e!=nil{t.Fatal(e)}
    c2sPacket:=v4RawC2STestPacket(draft.Ciphertext,b.rxBoundary,b.originalFlow)
    if e:=syscall.Sendto(rawFeedback,c2sPacket,0,
        &syscall.SockaddrInet4{Addr:b.originalFlow.ServerIP});e!=nil{
        t.Fatalf("client authenticated FEC M2 kernel TX: %v",e)
    }
    if e:=releaseClient.feedbackKernelResult(draft.RecordPN,1);e!=nil{
        t.Fatalf("client M2 actual kernel send classification: %v",e)
    }
    acceptedM2:=false
    for deadline:=time.Now().Add(350*time.Millisecond);
        time.Now().Before(deadline);time.Sleep(5*time.Millisecond){
        coverage,e:=b.rustOwnerNormalM2Coverage()
        if e!=nil{t.Fatalf("original Rust M2 coverage readback: %v",e)}
        if coverage.AuthenticatedReverseReports>=1{
            acceptedM2=true;break
        }
    }
    if !acceptedM2{
        t.Fatal("original server moved C2S AEAD/replay owner did not accept real kernel authenticated client feedback")
    }
    // A source queued or even copied locally is NOT an authenticated
    // remote application-APPLIED receipt. Keep truthful pending.
    got,applied,e:=b.readbackOriginalFixedPending(pending,server.Epoch)
    if e!=nil||applied.Applied||got.AppliedRevision!=0{
        t.Fatalf("false product Fixed applied without actual peer M2: %+v %+v %v",got,applied,e)
    }
    t.Logf("M0_REAL_ORIGINAL_GO_RELEASE_CLIENT_FEC2_TUN_UDP_RECOVERY_PASS kernel_records=%d application_ipv4=%d parity_silent=%d recovered_missing=%d client_udp=%d originalTLS=1 release_client_no_probe_receiver=1 M2_authenticated_C2S_real_kernel_reverse_accepted=1 pending_not_applied=1 FEC2_PRODUCT_OFF=1",
        recordsSeen,originalDelivered,paritySilent,recoveredFirst,len(clientDelivered))
}
