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
            // Original ciphertext at PN=0 was already delivered. Re-inject
            // EXACT SAME immutable bytes through the real raw socket: the
            // Rust M1/M3 PN replay gate must reject, never release a second
            // business datagram. Next flip one cipher byte but rebuild real
            // IPv4/TCP checksums so it passes platform preflight; AEAD must
            // reject that independently. Neither path is FEC/repair.
            corrupt:=append([]byte(nil),wire...)
            corrupt[len(corrupt)/2]^=0x80
            rejected:=[][]byte{wire,corrupt}
            for index,badRecord:=range rejected{
                rawBad:=v4RawC2STestPacket(badRecord,bridge.rxBoundary,bridge.originalFlow)
                if err:=syscall.Sendto(rawfd,rawBad,0,
                    &syscall.SockaddrInet4{Addr:bridge.originalFlow.ServerIP});err!=nil{
                    t.Fatalf("raw negative send type=%d: %v",index,err)
                }
                got,failed,err:=bridge.receiveRawToTun()
                if err==nil || got!=0{
                    t.Fatalf("replayed/tampered ciphertext passed original M3 owner type=%d delivered=%d failed=%d err=%v",index,got,failed,err)
                }
                if err:=app.SetReadDeadline(time.Now().Add(40*time.Millisecond));err!=nil{t.Fatal(err)}
                tmp:=make([]byte,256)
                count,_,err:=app.ReadFromUDP(tmp)
                if err==nil || count!=0{
                    t.Fatalf("original Linux app received duplicate/corrupt payload type=%d n=%d err=%v",index,count,err)
                }
                ne,ok:=err.(net.Error)
                if !ok||!ne.Timeout(){t.Fatalf("negative app read non-timeout type=%d err=%v",index,err)}
            }
            t.Logf("EMBEDDED_REAL_RX_REPLAY_CORRUPT_NO_DELIVERY_PASS suite=%d",cipher)
            // TRUE independent S2C: application sends via real kernel TUN,
            // existing non-test embedded Rust M1/M3 seals original S2C PN,
            // actual M4 raw TX sends IPv4/TCP; independent Go raw socket
            // verifies exact tuple, TCP seq and original Go TLS S2C keys.
            rawPeer,e:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_TCP)
            if e!=nil{t.Fatalf("M4_RAW_PEER_UNSUPPORTED: %v",e)}
            defer syscall.Close(rawPeer)
            if e=syscall.Bind(rawPeer,&syscall.SockaddrInet4{Addr:bridge.originalFlow.ClientIP});e!=nil{
                t.Fatalf("kernel raw client bind: %v",e)
            }
            timeval:=syscall.NsecToTimeval((500*time.Millisecond).Nanoseconds())
            if e=syscall.SetsockoptTimeval(rawPeer,syscall.SOL_SOCKET,
                syscall.SO_RCVTIMEO,&timeval);e!=nil{t.Fatal(e)}
            reverse:=[]byte("embedded-TUN-kernel-to-real-raw-Go-peer")
            if wrote,e:=app.WriteToUDP(reverse,&net.UDPAddr{IP:senderIP,Port:42001});
                e!=nil||wrote!=len(reverse){t.Fatalf("kernel app reverse write n=%d err=%v",wrote,e)}
            pn2,seq2,packetLen,appLen,e:=bridge.tunToKernelRaw(uint32(ifi.Index))
            if e!=nil||pn2!=0||seq2!=bridge.txBoundary{
                t.Fatalf("original embedded Rust S2C PN/seq: pn=%d seq=%d boundary=%d err=%v",
                    pn2,seq2,bridge.txBoundary,e)
            }
            var cipherRecord []byte
            for attempt:=0;attempt<16;attempt++{
                buf:=make([]byte,2048)
                count,_,err:=syscall.Recvfrom(rawPeer,buf,0)
                if err!=nil{t.Fatalf("real Linux Go raw peer receive: %v",err)}
                if count<40||buf[0]>>4!=4||buf[9]!=6{continue}
                ihl:=int(buf[0]&0xf)*4
                if ihl<20||ihl+20>count{continue}
                if !bytes.Equal(buf[12:16],bridge.originalFlow.ServerIP[:])||
                   !bytes.Equal(buf[16:20],bridge.originalFlow.ClientIP[:])||
                   binary.BigEndian.Uint16(buf[ihl:ihl+2])!=bridge.originalFlow.ServerPort||
                   binary.BigEndian.Uint16(buf[ihl+2:ihl+4])!=bridge.originalFlow.ClientPort||
                   binary.BigEndian.Uint32(buf[ihl+4:ihl+8])!=seq2{continue}
                tcpLen:=int(buf[ihl+12]>>4)*4
                if tcpLen<20||ihl+tcpLen>count||uint32(count)!=packetLen{
                    t.Fatalf("invalid exact kernel raw TCP header packet=%d wanted=%d",count,packetLen)
                }
                cipherRecord=append([]byte(nil),buf[ihl+tcpLen:count]...)
                break
            }
            if len(cipherRecord)==0{t.Fatal("embedded original Rust M4 S2C raw not observed")}
            clientLimit,_:=c.RecordLimits()
            opener,e:=tlsrecord.NewOpenerForCipher(c.DirectionKeys().S2C,int(clientLimit),cipher)
            if e!=nil{t.Fatal(e)}
            opened,e:=opener.OpenRecord(cipherRecord)
            if e!=nil||opened.PN!=pn2||opened.Kind!=tlsrecord.KindLINK{
                t.Fatalf("verified original Go S2C AEAD/PN failed: %v %+v",e,opened)
            }
            inner:=opened.Payload
            if len(inner)!=int(appLen)||len(inner)<28+len(reverse)||
               inner[0]!=0x45||inner[9]!=17||
               !net.IP(inner[12:16]).Equal(dstIP)||
               !net.IP(inner[16:20]).Equal(senderIP)||
               !bytes.Equal(inner[28:],reverse){
                t.Fatalf("real S2C authenticated application mismatch got=%x appLen=%d",inner,appLen)
            }
            t.Logf("EMBEDDED_REAL_TUN_TO_RAW_GO_PEER_PASS suite=%d bytes=%d pn=%d seq=%d",
                cipher,len(reverse),pn2,seq2)
            if e=bridge.stopRelease();e!=nil{t.Fatal(e)}
            if _,_,_,_,e=bridge.tunToKernelRaw(uint32(ifi.Index));e==nil{
                t.Fatal("retired real M4 raw TX owner remained usable")
            }
            if _,e=bridge.state();e==nil{t.Fatal("stale released old Rust owner still visible")}
            if e=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);e!=nil{t.Fatal(e)}
        })
    }
}


// B03 bounded old/new generation isolation using two independently
// credential-checked Go protected TLS transactions and the SAME non-_test
// embedded Rust registry (no test-only owner). Retiring the old generation
// must not stop/consume the new session. This does not simulate M4 async loan.
func TestR0V4EmbeddedTwoGenerationStopIsolation(t *testing.T){
    oldStore,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
    newStore,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
    old:=&v4EmbeddedNativeBridge{}
    oldClient,oldServer,ce,se:=v4PairWithPrivateBridgeCipher(t,old,oldStore,CipherChaCha)
    if ce!=nil||se!=nil||oldClient==nil||oldServer==nil||!old.committed{
        t.Fatalf("old verified protected Go Rust admission: %v %v",ce,se)
    }
    oldHandle:=old.handle
    fresh:=&v4EmbeddedNativeBridge{}
    newClient,newServer,ce,se:=v4PairWithPrivateBridgeCipher(t,fresh,newStore,CipherChaCha)
    if ce!=nil||se!=nil||newClient==nil||newServer==nil||!fresh.committed{
        t.Fatalf("new verified protected Go Rust admission: %v %v",ce,se)
    }
    if oldHandle==0||fresh.handle==0||oldHandle==fresh.handle||
       oldHandle>>32>=fresh.handle>>32{
        t.Fatalf("generations not fresh and monotonic old=%d new=%d",oldHandle,fresh.handle)
    }
    if got,err:=v4EmbeddedNativeState(oldHandle);err!=nil||got!=2{
        t.Fatalf("old must be Active until its own Stop got=%d err=%v",got,err)
    }
    if err:=old.stopRelease();err!=nil{t.Fatal(err)}
    if err:=old.stopRelease();err!=nil{
        t.Fatalf("repeat Stop after quiesced release must be idempotent: %v",err)
    }
    if phase,err:=v4EmbeddedNativeState(oldHandle);err==nil{
        t.Fatalf("retired numeric old owner resurrected phase=%d",phase)
    }
    if got,err:=fresh.state();err!=nil||got!=2{
        t.Fatalf("old retirement stopped the fresh generation: phase=%d err=%v",got,err)
    }
    newHandle:=fresh.handle
    if err:=fresh.stopRelease();err!=nil{t.Fatal(err)}
    if err:=fresh.stopRelease();err!=nil{t.Fatal(err)}
    if err:=oldStore.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,oldServer.Epoch);err!=nil{t.Fatal(err)}
    if err:=newStore.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,newServer.Epoch);err!=nil{t.Fatal(err)}
    t.Logf("EMBEDDED_OLD_NEW_GENERATION_STOP_ISOLATION_PASS old=%d new=%d",oldHandle>>32,newHandle>>32)
}
