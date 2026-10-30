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
    for _,mode:=range []FecV2Mode{FecV2Fixed,FecV2Auto}{
        t.Run(string(mode),func(t *testing.T){
            realOriginalGoFec2LinuxMode(t,mode)
        })
    }
}
func realOriginalGoFec2LinuxMode(t *testing.T,mode FecV2Mode){
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
        Transport:FecV2Normal,Mode:mode,Profile:FecV2Mild,
        AutoPolicy:FecV2Conservative,ConfigRevision:4}
    if mode==FecV2Auto{
        start:=FecV2Mild
        cfg.StartProfile=&start
    }
    pending,ack,e:=b.stageOriginalFixedPending(cfg,FecV2State{},server.Epoch)
    if e!=nil||ack.Applied||ack.Rejected||pending.RequestedRevision!=4{
        t.Fatalf("original Go Fixed TLS stage %+v %+v %v",pending,ack,e)
    }
    if e:=b.attachRawRx(uint32(lo.Index));e!=nil{t.Fatal(e)}
    if e:=b.attachKernelTun(dev.Fd(),tunName);e!=nil{t.Fatal(e)}
    peer,err:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_TCP)
    if err!=nil{t.Fatal(err)}
    defer syscall.Close(peer)
    // The original TLS peer IP intentionally becomes local only after
    // the independent CLIENT TUN is created. Binding the observer before
    // then requires Linux IP_FREEBIND, not a preinstalled local address
    // that could bypass the actual missing-source->parity->TUN route.
    if err:=syscall.SetsockoptInt(peer,syscall.SOL_IP,15,1);err!=nil{
        t.Fatalf("raw peer IP_FREEBIND: %v",err)
    }
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
    // PLAN027: the original-Go authenticated client source/parity must
    // recover genuine Linux UDP over real TUN. Retired per-record M2
    // cannot silently produce fixed-revision Applied or positive loss.
    // Old standalone probe may still encode historic WBC4 for offline
    // oracle; the live sender intentionally does not call feedbackDue.
    coverage,e:=b.rustOwnerNormalM2Coverage()
    if e!=nil||coverage.AuthenticatedReverseReports!=0||coverage.Covered2s!=0{
        t.Fatalf("retired M2 unexpectedly accepted per-record feedback: coverage=%+v err=%v",coverage,e)
    }
    got,applied,e:=b.readbackOriginalFixedPending(pending,server.Epoch)
    if e!=nil||applied.Applied||got.AppliedRevision!=0{
        t.Fatalf("Fixed/Auto false Applied without new authenticated witness: %+v %+v %v",got,applied,e)
    }
    if e:=b.commitOriginalFixedMatureM2(server.Epoch,4);e==nil{
        t.Fatal("retired M2 cannot grant legacy maturity and false Applied")
    }
    t.Logf("M0_REAL_ORIGINAL_GO_RELEASE_CLIENT_FEC2_TUN_UDP_RECOVERY_PASS mode=%s kernel_records=%d application_ipv4=%d parity_silent=%d recovered_missing=%d client_udp=%d originalTLS=1 no_per_record_receipt=1 fixed_applied=false",
        mode,recordsSeen,originalDelivered,paritySilent,recoveredFirst,len(clientDelivered))
    // M4 Linux lifecycle contract: after real traffic, Stop must join
    // native client borrow/receiver before the Go-owned TUN is released.
    // A second Stop is idempotent, and old epoch RX/feedback is rejected.
    if e:=releaseClient.stop();e!=nil{t.Fatalf("client native Stop: %v",e)}
    if e:=releaseClient.stop();e!=nil{t.Fatalf("repeated client Stop: %v",e)}
    if _,e:=releaseClient.consumeAuthenticatedKernelRecord(
        make([]byte,40));e==nil{
        t.Fatal("stopped client still accepts old-generation network RX")
    }
    if _,e:=releaseClient.feedbackDue();e==nil{
        t.Fatal("stopped client still issues feedback")
    }
    if e:=clientDev.Close();e!=nil{t.Fatalf("client TUN Go owner close: %v",e)}
    if _,e:=net.InterfaceByName(clientName);e==nil{
        t.Fatal("native client TUN interface leaked after native Stop + Go fd close")
    }
    if e:=b.stopRelease();e!=nil{t.Fatalf("server Rust original Stop: %v",e)}
    if e:=dev.Close();e!=nil{t.Fatalf("server TUN Go owner close: %v",e)}
    if _,e:=net.InterfaceByName(tunName);e==nil{
        t.Fatal("server TUN interface leaked after native Stop + Go fd close")
    }
    if mode==FecV2Auto{
        t.Log("M0_PLAN027_ORIGINAL_GO_FEC2_AUTO_START_PENDING_NO_M2_PASS startup_profile=mild bounded_unknown_feedback=hold legacy_applied=false client_udp=4")
    }else{
        t.Log("M0_PLAN027_ORIGINAL_GO_FEC2_FIXED_PENDING_NO_M2_PASS kernel_source_parity=1 legacy_applied=false client_udp=4 no_fake_apply=1")
    }
    t.Log("M4_LINUX_ORIGINAL_GO_CONNECT_FEC_REAL_NETNS_CLIENT_SERVER_STOP_OWNED_CLEANUP_PASS tls=1 client_udp=4 lost_source_recovered=1 repeated_stop=1 stale_rx_deny=1 stale_probe_feedback_deny=1 both_tun_devices_gone=1")
}
