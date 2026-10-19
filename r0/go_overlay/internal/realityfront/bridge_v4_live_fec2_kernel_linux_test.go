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
    _,server,ce,se:=v4PairWithPrivateBridgeCipher(t,b,store,CipherChaCha,true)
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
    blocks:=map[uint64]bool{}
    kinds:=map[uint64]int{}
    delivered:=map[string]bool{}
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
        block,index,recovered,plain,e:=b.fec2ProbeLivePeerConsume(wire)
        if e!=nil{t.Fatalf("original Go TLS keyed independent M3 FEC peer: %v",e)}
        if len(plain)==0{
            // A verified kind3 parity with no missing source emits no
            // application candidate. It still passed native AEAD+RS16
            // grammar checks and unique replay PN.
            continue
        }
        if block==0||index!=0||recovered||len(plain)<28+64||
            plain[0]>>4!=4||plain[9]!=17{
            t.Fatalf("first source not IPv4 application block=%d idx=%d len=%d",block,index,len(plain))
        }
        udp:=string(plain[len(plain)-64:])
        if !expected[udp]||delivered[udp]{
            t.Fatalf("wrong/duplicate real Go TUN UDP source block=%d",block)
        }
        delivered[udp]=true
        blocks[block]=true
        kinds[block]++
        if len(blocks)==packets{break}
    }
    if len(blocks)<2||len(delivered)<2{
        t.Fatalf("real original Go continuous kernel FEC source incomplete blocks=%d app=%d",len(blocks),len(delivered))
    }
    // A source queued or even copied locally is NOT an authenticated
    // remote application-APPLIED receipt. Keep truthful pending.
    got,applied,e:=b.readbackOriginalFixedPending(pending,server.Epoch)
    if e!=nil||applied.Applied||got.AppliedRevision!=0{
        t.Fatalf("false product Fixed applied without actual peer M2: %+v %+v %v",got,applied,e)
    }
    t.Logf("M0_REAL_ORIGINAL_GO_BACKGROUND_FIXED_MULTIBLOCK_M4_SOURCE_PASS blocks=%d real_app_ipv4=%d M3_AEAD_peer=1 pending_not_applied=1 FEC2_PRODUCT_OFF=1",
        len(blocks),len(delivered))
}
