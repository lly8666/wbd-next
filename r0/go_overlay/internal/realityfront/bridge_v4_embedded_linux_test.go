//go:build linux && cgo && wbd_v4_embedded_go
package realityfront
import (
    "bytes"
    "encoding/binary"
    "fmt"
    "net"
    "os"
    "os/exec"
    "syscall"
    "testing"
    "time"
    "unsafe"

    "github.com/lly8666/wobuzhidao/internal/tlsrecord"
)
func TestR0V4EmbeddedNativeProtectedControlAllCiphers(t *testing.T){
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(string(rune('0'+cipher)),func(t *testing.T){
            store,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
            b:=&v4EmbeddedNativeBridge{}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,b,store,cipher)
            if ce!=nil||se!=nil||client==nil||server==nil||
               !b.committed||b.handle==0{
                t.Fatalf("real Go protected TLS embedded Rust commit: client=%v server=%v",ce,se)
            }
            state,err:=b.state()
            if err!=nil||state!=2{t.Fatalf("owner phase=%d err=%v",state,err)}
            if err:=b.stopRelease();err!=nil{t.Fatal(err)}
            if _,err:=b.state();err==nil{t.Fatal("released owner still visible")}
            if err:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);err!=nil{t.Fatal(err)}
        })
    }
}


// Real kernel C2S product-path anchor through the NON-_test Go→Rust owner.
// No separate test activation or decrypt/delivery oracle: actual M4 raw FD,
// original M1 slab and M3 AEAD, M4 TUN FD and application UDP socket.
func TestR0V4EmbeddedRealM4RawToTun(t *testing.T){
    if os.Getenv("WBD_REAL_TUN")!="1"{t.Skip("isolated CAP_NET_ADMIN netns only")}
    const name="wbdemtu0"
    tun,e:=os.OpenFile("/dev/net/tun",os.O_RDWR,0)
    if e!=nil{t.Fatal(e)}
    defer tun.Close()
    var ifreq [40]byte
    copy(ifreq[:16],[]byte(name))
    binary.LittleEndian.PutUint16(ifreq[16:18],0x1001)
    _,_,errno:=syscall.Syscall(syscall.SYS_IOCTL,tun.Fd(),0x400454ca,
        uintptr(unsafe.Pointer(&ifreq[0])))
    if errno!=0{t.Fatalf("real TUN create: %v",errno)}
    for _,args:=range [][]string{{"addr","add","10.241.20.1/24","dev",name},{"link","set","dev",name,"up"}}{
        if out,e:=exec.Command("ip",args...).CombinedOutput();e!=nil{t.Fatalf("TUN config %v: %v %s",args,e,out)}
    }
    ifi,e:=net.InterfaceByName("lo")
    if e!=nil||ifi.Index<=0{t.Fatalf("real lo: %v",e)}
    dstIP:=net.IPv4(10,241,20,1); senderIP:=net.IPv4(10,241,20,2)
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(fmt.Sprintf("suite-%d",cipher),func(t *testing.T){
            store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
            bridge:=&v4EmbeddedNativeBridge{}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,bridge,store,cipher)
            if ce!=nil||se!=nil||client==nil||server==nil||!bridge.committed{
                t.Fatalf("Go TLS protected owner invalid: %v %v",ce,se)
            }
            if bridge.originalFlow.ClientIP!=([4]byte{10,0,0,2})||
                bridge.originalFlow.ServerIP!=([4]byte{10,0,1,1})||
                bridge.originalFlow.ClientPort!=41001||bridge.originalFlow.ServerPort!=443{
                t.Fatalf("original FakeTCP SYN tuple changed: %+v",bridge.originalFlow)
            }
            if e=bridge.attachRawRx(uint32(ifi.Index));e!=nil{t.Fatal(e)}
            if e=bridge.attachRawRx(uint32(ifi.Index));e==nil{
                t.Fatal("double binding same driver accepted")
            }
            if e=bridge.attachKernelTun(tun.Fd(),name);e!=nil{t.Fatal(e)}
            app,e:=net.ListenUDP("udp4",&net.UDPAddr{IP:dstIP,Port:0})
            if e!=nil{t.Fatal(e)}
            defer app.Close()
            c,e:=client.ColdSnapshot();if e!=nil{t.Fatal(e)}
            _,limit:=c.RecordLimits()
            sealer,e:=tlsrecord.NewSealerForCipher(c.DirectionKeys().C2S,int(limit),cipher)
            if e!=nil{t.Fatal(e)}
            payload:=[]byte("embedded-verified-raw-TUN-first")
            packet:=make([]byte,28+len(payload))
            packet[0]=0x45;packet[8]=64;packet[9]=17
            binary.BigEndian.PutUint16(packet[2:4],uint16(len(packet)))
            binary.BigEndian.PutUint16(packet[4:6],uint16(31+cipher))
            copy(packet[12:16],senderIP.To4());copy(packet[16:20],dstIP.To4())
            binary.BigEndian.PutUint16(packet[10:12],v4RawCheckSum(packet[:20]))
            binary.BigEndian.PutUint16(packet[20:22],40001)
            binary.BigEndian.PutUint16(packet[22:24],uint16(app.LocalAddr().(*net.UDPAddr).Port))
            binary.BigEndian.PutUint16(packet[24:26],uint16(8+len(payload)))
            copy(packet[28:],payload)
            wire,pn,e:=sealer.Seal(packet);if e!=nil||pn!=0{t.Fatalf("real Go C2S seal: %v pn=%d",e,pn)}
            rawfd,e:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_RAW)
            if e!=nil{t.Fatal(e)}
            defer syscall.Close(rawfd)
            if e=syscall.SetsockoptInt(rawfd,syscall.IPPROTO_IP,syscall.IP_HDRINCL,1);e!=nil{t.Fatal(e)}
            raw:=v4RawC2STestPacket(wire,bridge.rxBoundary,bridge.originalFlow)
            if e=syscall.Sendto(rawfd,raw,0,&syscall.SockaddrInet4{Addr:bridge.originalFlow.ServerIP});e!=nil{t.Fatal(e)}
            delivered,failed,e:=bridge.receiveRawToTun()
            if e!=nil||delivered!=1||failed!=0{t.Fatalf("embedded real M4 raw to app %v delivered=%d failed=%d",e,delivered,failed)}
            if e=app.SetReadDeadline(time.Now().Add(2*time.Second));e!=nil{t.Fatal(e)}
            received:=make([]byte,256)
            n,peer,e:=app.ReadFromUDP(received)
            if e!=nil||peer==nil||!peer.IP.Equal(senderIP)||!bytes.Equal(received[:n],payload){
                t.Fatalf("NO embedded owner real TUN application packet: err=%v peer=%v n=%d",e,peer,n)
            }
            t.Logf("EMBEDDED_REAL_RAW_TO_TUN_APP_PASS suite=%d bytes=%d",cipher,n)
            if e=bridge.stopRelease();e!=nil{t.Fatal(e)}
            if _,e=bridge.state();e==nil{t.Fatal("stale released old Rust owner still visible")}
            if e=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);e!=nil{t.Fatal(e)}
        })
    }
}
