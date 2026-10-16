//go:build linux && cgo && wbd_v4_embedded_go
package realityfront
import (
    "bytes"
    "encoding/binary"
    "errors"
    "fmt"
    "net"
    "os"
    "os/exec"
    "regexp"
    "strconv"
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
            // A second genuine app packet uses the SAME verified Go session,
            // original Rust M1/M3 owner and kernel M4 raw/TUN devices.
            // Distinct PN=1 and the next exact TCP sequence must succeed:
            // a one-packet fixture must never pass as a steady-state path.
            packet2:=append([]byte(nil),packet...)
            payload2:=bytes.Repeat([]byte{0x5a},len(payload))
            copy(packet2[28:],payload2)
            binary.BigEndian.PutUint16(packet2[4:6],uint16(49+cipher))
            binary.BigEndian.PutUint16(packet2[10:12],0)
            binary.BigEndian.PutUint16(packet2[10:12],v4RawCheckSum(packet2[:20]))
            wire2,pnNext,e:=sealer.Seal(packet2)
            if e!=nil||pnNext!=1{t.Fatalf("second original TLS C2S PN want1 got=%d err=%v",pnNext,e)}
            seqNext:=bridge.rxBoundary+uint32(len(wire))
            rawNext:=v4RawC2STestPacket(wire2,seqNext,bridge.originalFlow)
            if e=syscall.Sendto(rawfd,rawNext,0,&syscall.SockaddrInet4{Addr:bridge.originalFlow.ServerIP});e!=nil{
                t.Fatalf("second real kernel raw C2S send: %v",e)
            }
            delivered,failed,e=bridge.receiveRawToTun()
            if e!=nil||delivered!=1||failed!=0{
                t.Fatalf("second same-generation C2S owner failed: delivered=%d failed=%d err=%v",delivered,failed,e)
            }
            if e=app.SetReadDeadline(time.Now().Add(2*time.Second));e!=nil{t.Fatal(e)}
            got2:=make([]byte,256)
            n2,peer2,e:=app.ReadFromUDP(got2)
            if e!=nil||peer2==nil||!peer2.IP.Equal(senderIP)||!bytes.Equal(got2[:n2],payload2){
                t.Fatalf("second kernel TUN app delivery not continuous: err=%v peer=%v n=%d",e,peer2,n2)
            }
            t.Logf("EMBEDDED_REAL_C2S_SECOND_PACKET_PASS suite=%d bytes=%d pn=%d seq=%d",
                cipher,n2,pnNext,seqNext)
            // SAME Go credential-checked protected session and original
            // M1/M3/M4 owner; ordinary unfragmented LINK has NO LINK20
            // header. Only fragmented packets pay LINK_HEADER=20.
            // Exact ordinary size limit = negotiated wire 1400 - RECORD31.
            // Never change the negotiated limit, TUN MTU or sender seed.
            const recordFixed=31
            const ipUDPHeaders=28
            if limit!=1400{t.Fatalf("actual protected Go server wire limit unexpectedly %d",limit)}
            maxIP:=int(limit)-recordFixed
            if maxIP<=ipUDPHeaders||maxIP>=1500{
                t.Fatalf("unsafe actual effective IPv4 business limit %d",maxIP)
            }
            makeUDPIP:=func(ipLen int, fill byte)[]byte{
                ipPacket:=make([]byte,ipLen)
                ipPacket[0]=0x45;ipPacket[8]=64;ipPacket[9]=17
                binary.BigEndian.PutUint16(ipPacket[2:4],uint16(ipLen))
                binary.BigEndian.PutUint16(ipPacket[4:6],uint16(99+cipher))
                copy(ipPacket[12:16],senderIP.To4())
                copy(ipPacket[16:20],dstIP.To4())
                binary.BigEndian.PutUint16(ipPacket[10:12],v4RawCheckSum(ipPacket[:20]))
                binary.BigEndian.PutUint16(ipPacket[20:22],40001)
                binary.BigEndian.PutUint16(ipPacket[22:24],
                    uint16(app.LocalAddr().(*net.UDPAddr).Port))
                binary.BigEndian.PutUint16(ipPacket[24:26],uint16(ipLen-20))
                for i:=28;i<len(ipPacket);i++{ipPacket[i]=fill}
                return ipPacket
            }
            lastSeq:=seqNext+uint32(len(wire2))
            atLimit:=makeUDPIP(maxIP,0x6b)
            atWire,atPN,err:=sealer.Seal(atLimit)
            if err!=nil||atPN!=2||len(atWire)>int(limit){
                t.Fatalf("cannot seal actual near-limit record pn=%d wire=%d err=%v",atPN,len(atWire),err)
            }
            if err:=syscall.Sendto(rawfd,
                v4RawC2STestPacket(atWire,lastSeq,bridge.originalFlow),0,
                &syscall.SockaddrInet4{Addr:bridge.originalFlow.ServerIP});err!=nil{
                t.Fatalf("real raw effective boundary packet: %v",err)
            }
            maxDelivered,maxFailed,maxErr:=bridge.receiveRawToTun()
            if maxErr!=nil||maxDelivered!=1||maxFailed!=0{
                t.Fatalf("original Rust normal-off exact max=%d rejected delivered=%d failed=%d err=%v",
                    maxIP,maxDelivered,maxFailed,maxErr)
            }
            if err:=app.SetReadDeadline(time.Now().Add(2*time.Second));err!=nil{t.Fatal(err)}
            largeRecv:=make([]byte,maxIP)
            size,from,err:=app.ReadFromUDP(largeRecv)
            if err!=nil||from==nil||!from.IP.Equal(senderIP)||
                size!=maxIP-ipUDPHeaders||
                !bytes.Equal(largeRecv[:size],atLimit[ipUDPHeaders:]){
                t.Fatalf("real TUN max-frame app mismatch n=%d expected=%d peer=%v err=%v",
                    size,maxIP-ipUDPHeaders,from,err)
            }
            t.Logf("EMBEDDED_REAL_MTU_EXACT_BOUNDARY_PASS suite=%d ip_bytes=%d payload=%d pn=%d",
                cipher,maxIP,size,atPN)
            // 1401-byte record cannot be formed by original trusted
            // Go TLS sealer: oversized ordinary packet must fail BEFORE
            // any transmission. Its failed attempt is NOT a valid AEAD
            // record; do not pretend it had authenticated successfully.
            overIP:=makeUDPIP(maxIP+1,0x4c)
            _,attemptedPN,err:=sealer.Seal(overIP)
            if !errors.Is(err,tlsrecord.ErrPayloadTooLarge){
                t.Fatalf("negotiated 1400B record limit not enforced for IP=%d: pn=%d err=%v",
                    maxIP+1,attemptedPN,err)
            }
            // Independently exercise real M4 Linux raw ingress with an
            // overlong/invalid encrypted record constructed from a valid
            // boundary frame plus one appended byte. TCP checksum is
            // recalculated by v4RawC2STestPacket; original Rust record
            // length guard MUST refuse it before TUN application delivery.
            oversizedWire:=append(append([]byte(nil),atWire...),0x4c)
            if len(oversizedWire)!=int(limit)+1{
                t.Fatalf("bad over-limit record fixture length=%d",len(oversizedWire))
            }
            if err:=syscall.Sendto(rawfd,
                v4RawC2STestPacket(oversizedWire,lastSeq+uint32(len(atWire)),
                    bridge.originalFlow),0,
                &syscall.SockaddrInet4{Addr:bridge.originalFlow.ServerIP});err!=nil{
                t.Fatalf("real raw oversized encrypted record send: %v",err)
            }
            overDelivered,_,overErr:=bridge.receiveRawToTun()
            if overErr==nil||overDelivered!=0{
                t.Fatalf("overlong record was accepted by original M4/M1/M3: delivered=%d err=%v",
                    overDelivered,overErr)
            }
            if err:=app.SetReadDeadline(time.Now().Add(40*time.Millisecond));err!=nil{t.Fatal(err)}
            shouldBeEmpty:=make([]byte,maxIP+1)
            nOver,_,appErr:=app.ReadFromUDP(shouldBeEmpty)
            ne,timeout:=appErr.(net.Error)
            if nOver!=0||!timeout||!ne.Timeout(){
                t.Fatalf("over-MTU business leaked to independent kernel app n=%d err=%v",nOver,appErr)
            }
            t.Logf("EMBEDDED_REAL_MTU_OVER_LIMIT_FAIL_CLOSED_PASS suite=%d denied_ip=%d denied_record_wire=%d",
                cipher,maxIP+1,len(oversizedWire))
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
            // Same real TUN-backed Go application, same M1 slab/AEAD owner
            // and retained M4 raw TX: PN must advance rather than starting
            // another owner or replaying the first S2C TCP sequence.
            reverse2:=[]byte("embedded-second-TUN-to-raw-Go-peer")
            if wrote,err:=app.WriteToUDP(reverse2,&net.UDPAddr{IP:senderIP,Port:42001});
                err!=nil||wrote!=len(reverse2){
                t.Fatalf("second Go app TUN ingress n=%d err=%v",wrote,err)
            }
            pn3,seq3,packetLen3,appLen3,err:=bridge.tunToKernelRaw(uint32(ifi.Index))
            if err!=nil||pn3!=1||seq3!=seq2+uint32(len(cipherRecord)){
                t.Fatalf("second embedded S2C PN/seq wrong pn=%d seq=%d prev=%d record=%d err=%v",
                    pn3,seq3,seq2,len(cipherRecord),err)
            }
            var record2 []byte
            for attempt:=0;attempt<16;attempt++{
                buf:=make([]byte,2048)
                count,_,recvErr:=syscall.Recvfrom(rawPeer,buf,0)
                if recvErr!=nil{t.Fatalf("second Linux raw peer receive: %v",recvErr)}
                if count<40||buf[0]>>4!=4||buf[9]!=6{continue}
                ihl:=int(buf[0]&0xf)*4
                if ihl<20||ihl+20>count{continue}
                if !bytes.Equal(buf[12:16],bridge.originalFlow.ServerIP[:])||
                   !bytes.Equal(buf[16:20],bridge.originalFlow.ClientIP[:])||
                   binary.BigEndian.Uint16(buf[ihl:ihl+2])!=bridge.originalFlow.ServerPort||
                   binary.BigEndian.Uint16(buf[ihl+2:ihl+4])!=bridge.originalFlow.ClientPort||
                   binary.BigEndian.Uint32(buf[ihl+4:ihl+8])!=seq3{continue}
                tcpLen:=int(buf[ihl+12]>>4)*4
                if tcpLen<20||ihl+tcpLen>count||uint32(count)!=packetLen3{
                    t.Fatalf("invalid second kernel raw packet n=%d want=%d",count,packetLen3)
                }
                record2=append([]byte(nil),buf[ihl+tcpLen:count]...)
                break
            }
            if len(record2)==0{t.Fatal("second original M4 raw S2C missing")}
            opened2,err:=opener.OpenRecord(record2)
            if err!=nil||opened2.PN!=pn3||opened2.Kind!=tlsrecord.KindLINK{
                t.Fatalf("second independent Go TLS AEAD/PN invalid err=%v opened=%+v",err,opened2)
            }
            inner2:=opened2.Payload
            if len(inner2)!=int(appLen3)||len(inner2)<28+len(reverse2)||
                inner2[0]!=0x45||inner2[9]!=17||
                !net.IP(inner2[12:16]).Equal(dstIP)||
                !net.IP(inner2[16:20]).Equal(senderIP)||
                !bytes.Equal(inner2[28:],reverse2){
                t.Fatalf("second S2C app payload mismatch got=%x want=%x",inner2,reverse2)
            }
            t.Logf("EMBEDDED_REAL_S2C_SECOND_PACKET_PASS suite=%d bytes=%d pn=%d seq=%d",
                cipher,len(reverse2),pn3,seq3)
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



// Exactly one PRIVATE protected Go TLS session and one ordinary Rust M1/M3
// generation per suite, with both real Linux M4 raw and TUN drivers. Bounded
// 12-packet bidirectional observation; NOT a bandwidth/p99 benchmark. The
// optional loss case reports missing packets without assuming recovery.
func TestR0V4EmbeddedSteadyBurst(t *testing.T) {
    if os.Getenv("WBD_REAL_TUN")!="1"||os.Getenv("WBD_M0_STEADY_BURST")!="1" {
        t.Skip("owned privileged netns only")
    }
    lossy:=os.Getenv("WBD_M0_STEADY_LOSS_PERCENT")=="1"
    const packets=12
    const tunName="wbdmbur0"
    f,err:=os.OpenFile("/dev/net/tun",os.O_RDWR,0)
    if err!=nil{t.Fatal(err)}
    defer f.Close()
    var req [40]byte
    copy(req[:16],[]byte(tunName))
    binary.LittleEndian.PutUint16(req[16:18],0x1001)
    _,_,errno:=syscall.Syscall(syscall.SYS_IOCTL,f.Fd(),0x400454ca,
        uintptr(unsafe.Pointer(&req[0])))
    if errno!=0{t.Fatalf("real TUN create: %v",errno)}
    for _,args:=range [][]string{{"addr","add","10.241.21.1/24","dev",tunName},
        {"link","set","dev",tunName,"up"}} {
        if out,e:=exec.Command("ip",args...).CombinedOutput();e!=nil{
            t.Fatalf("real TUN config %v: %v %s",args,e,out)
        }
    }
    dst:=net.IPv4(10,241,21,1);src:=net.IPv4(10,241,21,2)
    lo,err:=net.InterfaceByName("lo")
    if err!=nil||lo.Index<1{t.Fatalf("real lo: %v",err)}
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256} {
        t.Run(fmt.Sprintf("suite-%d",cipher),func(t *testing.T){
            store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
            b:=&v4EmbeddedNativeBridge{}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,b,store,cipher)
            if ce!=nil||se!=nil||client==nil||server==nil||!b.committed{
                t.Fatalf("original private Go TLS protected session invalid: %v %v",ce,se)
            }
            t.Cleanup(func(){
                if err:=b.stopRelease();err!=nil{t.Errorf("real owner stop: %v",err)}
                if err:=store.ReleaseLane("protected-owner",
                   []byte("0123456789abcdef"),1,server.Epoch);err!=nil{
                    t.Errorf("original Go lane release: %v",err)
                }
            })
            if e:=b.attachRawRx(uint32(lo.Index));e!=nil{t.Fatal(e)}
            if e:=b.attachKernelTun(f.Fd(),tunName);e!=nil{t.Fatal(e)}
            app,e:=net.ListenUDP("udp4",&net.UDPAddr{IP:dst,Port:0})
            if e!=nil{t.Fatal(e)}
            defer app.Close()
            raw,e:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_RAW)
            if e!=nil{t.Fatal(e)}
            defer syscall.Close(raw)
            if e:=syscall.SetsockoptInt(raw,syscall.IPPROTO_IP,syscall.IP_HDRINCL,1);e!=nil{t.Fatal(e)}
            peer,e:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_TCP)
            if e!=nil{t.Fatal(e)}
            defer syscall.Close(peer)
            if e:=syscall.Bind(peer,&syscall.SockaddrInet4{Addr:b.originalFlow.ClientIP});e!=nil{t.Fatal(e)}
            tm:=syscall.NsecToTimeval((150*time.Millisecond).Nanoseconds())
            if e:=syscall.SetsockoptTimeval(peer,syscall.SOL_SOCKET,syscall.SO_RCVTIMEO,&tm);e!=nil{t.Fatal(e)}
            cold,e:=client.ColdSnapshot();if e!=nil{t.Fatal(e)}
            clientLimit,serverLimit:=cold.RecordLimits()
            seal,e:=tlsrecord.NewSealerForCipher(cold.DirectionKeys().C2S,int(serverLimit),cipher)
            if e!=nil{t.Fatal(e)}
            open,e:=tlsrecord.NewOpenerForCipher(cold.DirectionKeys().S2C,int(clientLimit),cipher)
            if e!=nil{t.Fatal(e)}
            cseq:=b.rxBoundary;sseq:=b.txBoundary
            cSent,cDelivered,sSent,sDelivered:=0,0,0,0
            cBytes,sBytes:=0,0
            cMiss,sMiss:=0,0
            start:=time.Now()
            for i:=0;i<packets;i++{
                cp:=bytes.Repeat([]byte{byte(0x30+i)},48+i%4)
                ip:=make([]byte,28+len(cp))
                ip[0]=0x45;ip[8]=64;ip[9]=17
                binary.BigEndian.PutUint16(ip[2:4],uint16(len(ip)))
                binary.BigEndian.PutUint16(ip[4:6],uint16(210+i))
                copy(ip[12:16],src.To4());copy(ip[16:20],dst.To4())
                binary.BigEndian.PutUint16(ip[10:12],v4RawCheckSum(ip[:20]))
                binary.BigEndian.PutUint16(ip[20:22],40001)
                binary.BigEndian.PutUint16(ip[22:24],uint16(app.LocalAddr().(*net.UDPAddr).Port))
                binary.BigEndian.PutUint16(ip[24:26],uint16(8+len(cp)))
                copy(ip[28:],cp)
                encrypted,pn,err:=seal.Seal(ip)
                if err!=nil||pn!=uint64(i){t.Fatalf("C2S real Go TLS PN=%d want=%d err=%v",pn,i,err)}
                if err:=syscall.Sendto(raw,v4RawC2STestPacket(encrypted,cseq,b.originalFlow),0,
                    &syscall.SockaddrInet4{Addr:b.originalFlow.ServerIP});err!=nil{t.Fatal(err)}
                cSent++;cBytes+=len(cp)
                cseq+=uint32(len(encrypted))
                delivered,failed,rxErr:=b.receiveRawToTun()
                if rxErr==nil && delivered==1 && failed==0 {
                    if e:=app.SetReadDeadline(time.Now().Add(200*time.Millisecond));e!=nil{t.Fatal(e)}
                    buff:=make([]byte,256)
                    n,from,readErr:=app.ReadFromUDP(buff)
                    if readErr==nil&&from!=nil&&from.IP.Equal(src)&&bytes.Equal(buff[:n],cp){
                        cDelivered++
                    }else if !lossy {
                        t.Fatalf("C2S kernel app missing/wrong at i=%d err=%v n=%d peer=%v",i,readErr,n,from)
                    }else{cMiss++}
                }else if !lossy{
                    t.Fatalf("C2S original Rust raw/TUN i=%d delivered=%d failed=%d err=%v",
                        i,delivered,failed,rxErr)
                }else{cMiss++}
                reverse:=bytes.Repeat([]byte{byte(0x61+i)},50+i%3)
                nWrite,wErr:=app.WriteToUDP(reverse,&net.UDPAddr{IP:src,Port:42001})
                if wErr!=nil||nWrite!=len(reverse){t.Fatalf("real kernel reverse app send n=%d err=%v",nWrite,wErr)}
                sSent++;sBytes+=len(reverse)
                rpn,rseq,full,appLen,txErr:=b.tunToKernelRaw(uint32(lo.Index))
                if txErr!=nil||rpn!=uint64(i)||rseq!=sseq||appLen!=uint32(28+len(reverse)){
                    t.Fatalf("original Rust S2C PN/seq i=%d pn=%d seq=%d want=%d app=%d err=%v",
                        i,rpn,rseq,sseq,appLen,txErr)
                }
                if full<40{t.Fatalf("kernel raw full packet too short %d",full)}
                sseq+=full-40
                var data []byte
                for attempt:=0;attempt<8;attempt++{
                    rawBuf:=make([]byte,2048)
                    n,_,e:=syscall.Recvfrom(peer,rawBuf,0)
                    if e!=nil {
                        if !lossy{t.Fatalf("independent Go raw peer i=%d: %v",i,e)}
                        break
                    }
                    if n<40||rawBuf[0]>>4!=4||rawBuf[9]!=6{continue}
                    ihl:=int(rawBuf[0]&0xf)*4
                    if ihl<20||ihl+20>n{continue}
                    if !bytes.Equal(rawBuf[12:16],b.originalFlow.ServerIP[:])||
                       !bytes.Equal(rawBuf[16:20],b.originalFlow.ClientIP[:])||
                       binary.BigEndian.Uint16(rawBuf[ihl:ihl+2])!=b.originalFlow.ServerPort||
                       binary.BigEndian.Uint16(rawBuf[ihl+2:ihl+4])!=b.originalFlow.ClientPort||
                       binary.BigEndian.Uint32(rawBuf[ihl+4:ihl+8])!=rseq{continue}
                    h:=int(rawBuf[ihl+12]>>4)*4
                    if h<20||ihl+h>n||uint32(n)!=full{t.Fatalf("invalid real raw TCP header n=%d full=%d",n,full)}
                    data=append([]byte(nil),rawBuf[ihl+h:n]...);break
                }
                if len(data)==0 {
                    if !lossy{t.Fatalf("S2C kernel raw not received i=%d",i)}
                    sMiss++;continue
                }
                decoded,e:=open.OpenRecord(data)
                if e!=nil||decoded.PN!=rpn||decoded.Kind!=tlsrecord.KindLINK||
                   len(decoded.Payload)!=int(appLen)||
                   !bytes.Equal(decoded.Payload[28:],reverse){
                    t.Fatalf("S2C independent Go TLS auth/PN/payload i=%d err=%v got=%+v",i,e,decoded)
                }
                sDelivered++
            }
            elapsed:=time.Since(start)
            if !lossy&&(cDelivered!=packets||sDelivered!=packets||cMiss!=0||sMiss!=0){
                t.Fatalf("no-loss real Linux burst delivery incomplete C2S=%d S2C=%d",cDelivered,sDelivered)
            }
            t.Logf("EMBEDDED_STEADY_BURST_%s suite=%d c2s_sent=%d c2s_delivered=%d c2s_missing_or_rejected=%d c2s_bytes_sent=%d s2c_sent=%d s2c_delivered=%d s2c_missing_or_rejected=%d s2c_bytes_sent=%d elapsed_ns=%d",
                map[bool]string{true:"LOSS_OBSERVATION",false:"PASS"}[lossy],
                cipher,cSent,cDelivered,cMiss,cBytes,sSent,sDelivered,sMiss,sBytes,elapsed.Nanoseconds())
        })
    }
}



// A targeted *genuine encrypted DATA* loss, not random netem/control traffic.
// A kernel u32 classifier on the owned namespace's lo egress drops exactly
// the first (PN0) IPPROTO_TCP record of the REAL credential-verified Go
// session. Original Rust M1/M3 Normal/off must deliver distinct PN1 without
// awaiting missing TCP-like seq. Not a retransmission/repair qualification.
func TestR0V4EmbeddedKernelSpecificDataLossNoHOL(t *testing.T) {
    if os.Getenv("WBD_REAL_TUN")!="1" || os.Getenv("WBD_M0_TARGETED_DROP")!="1" {
        t.Skip("private owned Linux namespace only")
    }
    const tunName="wbdhol0"
    fd,err:=os.OpenFile("/dev/net/tun",os.O_RDWR,0)
    if err!=nil{t.Fatal(err)}
    defer fd.Close()
    var req [40]byte
    copy(req[:16],[]byte(tunName))
    binary.LittleEndian.PutUint16(req[16:18],0x1001)
    _,_,eno:=syscall.Syscall(syscall.SYS_IOCTL,fd.Fd(),0x400454ca,
        uintptr(unsafe.Pointer(&req[0])))
    if eno!=0{t.Fatalf("real TUN ioctl: %v",eno)}
    for _,args:=range [][]string{
        {"addr","add","10.241.22.1/24","dev",tunName},
        {"link","set","dev",tunName,"up"},
    }{
        if out,e:=exec.Command("ip",args...).CombinedOutput();e!=nil{
            t.Fatalf("TUN configure %v: %v %s",args,e,out)
        }
    }
    runTC:=func(args ...string) string {
        t.Helper()
        out,e:=exec.Command("tc",args...).CombinedOutput()
        if e!=nil{t.Fatalf("real kernel tc %v: %v %s",args,e,out)}
        return string(out)
    }
    runTC("qdisc","add","dev","lo","clsact")
    t.Cleanup(func(){_ =exec.Command("tc","qdisc","del","dev","lo","clsact").Run()})
    lo,err:=net.InterfaceByName("lo")
    if err!=nil||lo.Index<1{t.Fatal(err)}
    dst:=net.IPv4(10,241,22,1);src:=net.IPv4(10,241,22,2)
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(fmt.Sprintf("suite-%d",cipher),func(t *testing.T){
            store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
            bridge:=&v4EmbeddedNativeBridge{}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,bridge,store,cipher)
            if ce!=nil||se!=nil||client==nil||server==nil||!bridge.committed{
                t.Fatalf("real original protected Go TLS admission: %v %v",ce,se)
            }
            t.Cleanup(func(){
                if e:=bridge.stopRelease();e!=nil{t.Errorf("original M4 owner stop: %v",e)}
                if e:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);e!=nil{
                    t.Errorf("original Go epoch release: %v",e)
                }
            })
            if e:=bridge.attachRawRx(uint32(lo.Index));e!=nil{t.Fatal(e)}
            if e:=bridge.attachKernelTun(fd.Fd(),tunName);e!=nil{t.Fatal(e)}
            app,e:=net.ListenUDP("udp4",&net.UDPAddr{IP:dst,Port:0})
            if e!=nil{t.Fatal(e)}
            defer app.Close()
            raw,e:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_RAW)
            if e!=nil{t.Fatal(e)}
            defer syscall.Close(raw)
            if e:=syscall.SetsockoptInt(raw,syscall.IPPROTO_IP,syscall.IP_HDRINCL,1);e!=nil{t.Fatal(e)}
            cold,e:=client.ColdSnapshot();if e!=nil{t.Fatal(e)}
            _,limit:=cold.RecordLimits()
            sealer,e:=tlsrecord.NewSealerForCipher(cold.DirectionKeys().C2S,int(limit),cipher)
            if e!=nil{t.Fatal(e)}
            // IP identification is not credential authority; only selects a
            // full TCP/IP DATA packet for this kernel loss experiment.
            ipid:=uint16(0xb170)+uint16(cipher)
            pref:="77"
            runTC("filter","add","dev","lo","egress","protocol","ip",
                "pref",pref,"u32",
                "match","ip","src","10.0.0.2/32",
                "match","ip","dst","10.0.1.1/32",
                "match","ip","protocol","6","0xff",
                "match","u16",fmt.Sprintf("0x%04x",ipid),"0xffff","at","4",
                "action","drop")
            makeIP:=func(v byte)[]byte{
                payload:=bytes.Repeat([]byte{v},56)
                ip:=make([]byte,28+len(payload))
                ip[0]=0x45;ip[8]=64;ip[9]=17
                binary.BigEndian.PutUint16(ip[2:4],uint16(len(ip)))
                copy(ip[12:16],src.To4());copy(ip[16:20],dst.To4())
                binary.BigEndian.PutUint16(ip[10:12],v4RawCheckSum(ip[:20]))
                binary.BigEndian.PutUint16(ip[20:22],40001)
                binary.BigEndian.PutUint16(ip[22:24],uint16(app.LocalAddr().(*net.UDPAddr).Port))
                binary.BigEndian.PutUint16(ip[24:26],uint16(8+len(payload)))
                copy(ip[28:],payload)
                return ip
            }
            missing:=makeIP(0x71)
            later:=makeIP(0x72)
            first,pn0,e:=sealer.Seal(missing)
            if e!=nil||pn0!=0{t.Fatalf("original TLS missing PN0: %v pn=%d",e,pn0)}
            second,pn1,e:=sealer.Seal(later)
            if e!=nil||pn1!=1{t.Fatalf("original TLS later PN1: %v pn=%d",e,pn1)}
            // Preserve correct outer TCP/IP checksums while altering only
            // a public header routing selector; original full ciphertext
            // is unchanged and still authenticated at Rust, if it arrives.
            gone:=v4RawC2STestPacket(first,bridge.rxBoundary,bridge.originalFlow)
            binary.BigEndian.PutUint16(gone[4:6],ipid)
            binary.BigEndian.PutUint16(gone[10:12],0)
            binary.BigEndian.PutUint16(gone[10:12],v4RawCheckSum(gone[:20]))
            if e:=syscall.Sendto(raw,gone,0,&syscall.SockaddrInet4{
                Addr:bridge.originalFlow.ServerIP});e!=nil{t.Fatal(e)}
            nextSeq:=bridge.rxBoundary+uint32(len(first))
            next:=v4RawC2STestPacket(second,nextSeq,bridge.originalFlow)
            if e:=syscall.Sendto(raw,next,0,&syscall.SockaddrInet4{
                Addr:bridge.originalFlow.ServerIP});e!=nil{t.Fatal(e)}
            // The ONLY receive call sees PN1 if the old missing TCP-like
            // sequence is not blocking the original Rust steady owner.
            delivered,failed,e:=bridge.receiveRawToTun()
            if e!=nil||delivered!=1||failed!=0{
                t.Fatalf("original Rust M4 Normal/off HOL when PN0 absent, later PN1 not delivered: delivered=%d failed=%d err=%v",delivered,failed,e)
            }
            if e:=app.SetReadDeadline(time.Now().Add(time.Second));e!=nil{t.Fatal(e)}
            got:=make([]byte,256)
            n,peer,err:=app.ReadFromUDP(got)
            if err!=nil||peer==nil||!peer.IP.Equal(src)||!bytes.Equal(got[:n],later[28:]){
                t.Fatalf("independent kernel TUN app first arrival not PN1 err=%v peer=%v n=%d",err,peer,n)
            }
            if e:=app.SetReadDeadline(time.Now().Add(40*time.Millisecond));e!=nil{t.Fatal(e)}
            n,_,err=app.ReadFromUDP(got)
            ne,ok:=err.(net.Error)
            if n!=0||!ok||!ne.Timeout(){
                t.Fatalf("missing PN0 appeared at independent application n=%d err=%v",n,err)
            }
            actual:=runTC("-s","filter","show","dev","lo","egress","pref",pref)
            rx:=regexp.MustCompile(`dropped ([0-9]+)`).FindStringSubmatch(actual)
            if len(rx)!=2{t.Fatalf("kernel exact encrypted DATA classifier lacks drop counter: %s",actual)}
            drops,_:=strconv.Atoi(rx[1])
            if drops!=1{
                t.Fatalf("expected one real kernel IPv4/TCP encrypted DATA drop got=%d tc=%s",drops,actual)
            }
            t.Logf("EMBEDDED_REAL_TARGETED_ENCRYPTED_DATA_LOSS_NO_HOL_PASS suite=%d targeted_c2s_pn=0 kernel_drop=1 next_c2s_pn=1 later_payload_bytes=%d old_seq_hole_bytes=%d",
                cipher,n,len(first))
        })
        // Rules are removed after a suite, before the next admission.
        runTC("filter","del","dev","lo","egress","pref","77")
    }
}



// Functional gate for *autonomous* Rust owner processing: the Go test
// injects both directions without calling a per-packet bridge RX/TX helper.
// Rust threads poll real kernel raw and TUN devices and use the existing
// single M1/M3 AEAD/PN owner. This does NOT measure steady throughput.
func TestR0V4EmbeddedIndependentRustOwnerLoop(t *testing.T){
    if os.Getenv("WBD_REAL_TUN")!="1"||os.Getenv("WBD_M0_BACKGROUND_LOOP")!="1"{
        t.Skip("owned kernel namespace and developer feature only")
    }
    const tunName="wbdauto0"
    const packets=8 // correctness burst, NOT performance claim
    dev,err:=os.OpenFile("/dev/net/tun",os.O_RDWR,0)
    if err!=nil{t.Fatal(err)}
    defer dev.Close()
    var req [40]byte
    copy(req[:16],[]byte(tunName))
    binary.LittleEndian.PutUint16(req[16:18],0x1001)
    _,_,errno:=syscall.Syscall(syscall.SYS_IOCTL,dev.Fd(),0x400454ca,
        uintptr(unsafe.Pointer(&req[0])))
    if errno!=0{t.Fatalf("original TUN ioctl: %v",errno)}
    for _,args:=range [][]string{
        {"addr","add","10.241.23.1/24","dev",tunName},
        {"link","set","dev",tunName,"up"},
    }{
        if out,e:=exec.Command("ip",args...).CombinedOutput();e!=nil{
            t.Fatalf("TUN configure %v: %v %s",args,e,out)
        }
    }
    lo,err:=net.InterfaceByName("lo")
    if err!=nil{t.Fatal(err)}
    serverIP:=net.IPv4(10,241,23,1)
    remoteIP:=net.IPv4(10,241,23,2)
    app,err:=net.ListenUDP("udp4",&net.UDPAddr{IP:serverIP,Port:0})
    if err!=nil{t.Fatal(err)}
    defer app.Close()
    store,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
    b:=&v4EmbeddedNativeBridge{}
    client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,b,store,CipherChaCha)
    if ce!=nil||se!=nil||client==nil||server==nil||!b.committed{
        t.Fatalf("original real Go authenticated TLS must commit: %v %v",ce,se)
    }
    t.Cleanup(func(){
        if e:=b.stopRelease();e!=nil{t.Errorf("Rust workers Stop/Release: %v",e)}
        if e:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);e!=nil{
            t.Errorf("original Go lane release: %v",e)
        }
    })
    if e:=b.attachRawRx(uint32(lo.Index));e!=nil{t.Fatal(e)}
    if e:=b.attachKernelTun(dev.Fd(),tunName);e!=nil{t.Fatal(e)}
    raw,err:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_RAW)
    if err!=nil{t.Fatal(err)}
    defer syscall.Close(raw)
    if err:=syscall.SetsockoptInt(raw,syscall.IPPROTO_IP,syscall.IP_HDRINCL,1);err!=nil{t.Fatal(err)}
    peer,err:=syscall.Socket(syscall.AF_INET,syscall.SOCK_RAW,syscall.IPPROTO_TCP)
    if err!=nil{t.Fatal(err)}
    defer syscall.Close(peer)
    if err:=syscall.Bind(peer,&syscall.SockaddrInet4{Addr:b.originalFlow.ClientIP});err!=nil{t.Fatal(err)}
    timeout:=syscall.NsecToTimeval((200*time.Millisecond).Nanoseconds())
    if err:=syscall.SetsockoptTimeval(peer,syscall.SOL_SOCKET,syscall.SO_RCVTIMEO,&timeout);err!=nil{t.Fatal(err)}
    cold,err:=client.ColdSnapshot();if err!=nil{t.Fatal(err)}
    cLim,sLim:=cold.RecordLimits()
    seal,err:=tlsrecord.NewSealerForCipher(cold.DirectionKeys().C2S,int(sLim),CipherChaCha)
    if err!=nil{t.Fatal(err)}
    open,err:=tlsrecord.NewOpenerForCipher(cold.DirectionKeys().S2C,int(cLim),CipherChaCha)
    if err!=nil{t.Fatal(err)}
    if err:=b.startRustOwnerLoop(uint32(lo.Index));err!=nil{t.Fatal(err)}
    if err:=b.startRustOwnerLoop(uint32(lo.Index));err==nil{
        t.Fatal("second independent Rust loop start must reject double driver ownership")
    }
    // When raw RX has zero incoming DATA, S2C still makes independent
    // progress. This would hang if we ran blocking raw RX under the global
    // registry mutex without readiness multiplexing.
    first:=bytes.Repeat([]byte{0x61},52)
    if n,e:=app.WriteToUDP(first,&net.UDPAddr{IP:remoteIP,Port:42001});e!=nil||n!=len(first){
        t.Fatalf("Go real TUN ingress initial n=%d err=%v",n,e)
    }
    observed:=make(map[uint64]bool)
    recvOne:=func(deadline time.Time) error{
        for time.Now().Before(deadline){
            bytesIn:=make([]byte,2048)
            n,_,e:=syscall.Recvfrom(peer,bytesIn,0)
            if e!=nil{continue}
            if n<40||bytesIn[0]>>4!=4||bytesIn[9]!=6{continue}
            ihl:=int(bytesIn[0]&0xf)*4
            if ihl<20||ihl+20>n{continue}
            if !bytes.Equal(bytesIn[12:16],b.originalFlow.ServerIP[:])||
                !bytes.Equal(bytesIn[16:20],b.originalFlow.ClientIP[:])||
                binary.BigEndian.Uint16(bytesIn[ihl:ihl+2])!=b.originalFlow.ServerPort||
                binary.BigEndian.Uint16(bytesIn[ihl+2:ihl+4])!=b.originalFlow.ClientPort{continue}
            h:=int(bytesIn[ihl+12]>>4)*4
            if h<20||ihl+h>n{continue}
            // A real kernel raw TCP listener sees its own / the host's
            // ACK/RST control packets. Those are NOT original M4 encrypted
            // DATA and must never be passed to the independent Go AEAD
            // opener as records; no retune of Rust owner or crypto.
            if bytesIn[ihl+13]&0x08==0 || n-ihl-h<=31{continue}
            opened,e:=open.OpenRecord(bytesIn[ihl+h:n])
            if e!=nil||opened.Kind!=tlsrecord.KindLINK||len(opened.Payload)<28{
                return fmt.Errorf("original Rust background S2C AEAD invalid: %v",e)
            }
            want:=bytes.Repeat([]byte{0x61+byte(opened.PN)},52)
            if opened.PN>=packets||!bytes.Equal(opened.Payload[28:],want){
                return fmt.Errorf("S2C PN/payload invalid pn=%d",opened.PN)
            }
            if observed[opened.PN]{return fmt.Errorf("duplicate Rust S2C PN=%d",opened.PN)}
            observed[opened.PN]=true
            return nil
        }
        return fmt.Errorf("independent Go raw peer deadline")
    }
    if err:=recvOne(time.Now().Add(2*time.Second));err!=nil{t.Fatal(err)}
    if !observed[0]{t.Fatal("S2C no-HOL initial packet missing PN0")}
    // All later input is sent without waiting for earlier responses. No Go
    // callback to receiveRawToTun or tunToKernelRaw; Rust performs both.
    seq:=b.rxBoundary
    for i:=0;i<packets;i++{
        payload:=bytes.Repeat([]byte{0x31+byte(i)},48)
        ip:=make([]byte,28+len(payload))
        ip[0]=0x45;ip[8]=64;ip[9]=17
        binary.BigEndian.PutUint16(ip[2:4],uint16(len(ip)))
        copy(ip[12:16],remoteIP.To4())
        copy(ip[16:20],serverIP.To4())
        binary.BigEndian.PutUint16(ip[10:12],v4RawCheckSum(ip[:20]))
        binary.BigEndian.PutUint16(ip[20:22],40001)
        binary.BigEndian.PutUint16(ip[22:24],uint16(app.LocalAddr().(*net.UDPAddr).Port))
        binary.BigEndian.PutUint16(ip[24:26],uint16(len(ip)-20))
        copy(ip[28:],payload)
        record,pn,e:=seal.Seal(ip)
        if e!=nil||pn!=uint64(i){t.Fatalf("C2S source PN=%d err=%v",pn,e)}
        if e:=syscall.Sendto(raw,v4RawC2STestPacket(record,seq,b.originalFlow),0,
            &syscall.SockaddrInet4{Addr:b.originalFlow.ServerIP});e!=nil{t.Fatal(e)}
        seq+=uint32(len(record))
        if i>0 {
            down:=bytes.Repeat([]byte{0x61+byte(i)},52)
            if n,e:=app.WriteToUDP(down,&net.UDPAddr{IP:remoteIP,Port:42001});
                e!=nil||n!=len(down){t.Fatalf("S2C app injector n=%d err=%v",n,e)}
        }
    }
    for i:=0;i<packets;i++{
        if e:=app.SetReadDeadline(time.Now().Add(3*time.Second));e!=nil{t.Fatal(e)}
        buf:=make([]byte,256)
        n,from,e:=app.ReadFromUDP(buf)
        expected:=bytes.Repeat([]byte{0x31+byte(i)},48)
        if e!=nil||from==nil||!from.IP.Equal(remoteIP)||!bytes.Equal(buf[:n],expected){
            t.Fatalf("original Rust background C2S kernel TUN app i=%d n=%d err=%v",i,n,e)
        }
    }
    deadline:=time.Now().Add(3*time.Second)
    for len(observed)<packets{
        if e:=recvOne(deadline);e!=nil{t.Fatal(e)}
    }
    stats,e:=b.rustOwnerLoopStats()
    if e!=nil||stats.RxOK!=packets||stats.TxOK!=packets{
        t.Fatalf("original Rust live owner did not process both independent device streams: %+v %v",stats,e)
    }
    t.Logf("EMBEDDED_ORIGINAL_RUST_BACKGROUND_RX_TX_PASS C2S=%d S2C=%d threads=2 NoGoPerPacketHelpers=true errors_RX=%d errors_TX=%d",
        stats.RxOK,stats.TxOK,stats.RxErr,stats.TxErr)

    // Real netns route/MTU contraction while the SAME original Rust
    // generation remains Active. A just-observed route frame budget never
    // overrides the original M4 raw driver MTU lease: the driver must
    // reject even an otherwise small, correctly authenticated S2C record,
    // instead of silently submitting it through a stale interface scope.
    mtuRaw,err:=os.ReadFile("/sys/class/net/lo/mtu")
    if err!=nil{t.Fatal(err)}
    oldMTU,err:=strconv.Atoi(string(bytes.TrimSpace(mtuRaw)))
    if err!=nil||oldMTU<=1500{t.Fatalf("unexpected real loopback MTU=%d: %v",oldMTU,err)}
    t.Cleanup(func(){
        if out,e:=exec.Command("ip","link","set","dev","lo","mtu",
            strconv.Itoa(oldMTU)).CombinedOutput();e!=nil{
            t.Errorf("restore owned namespace kernel lo MTU: %v %s",e,out)
        }
    })
    if out,e:=exec.Command("ip","link","set","dev","lo","mtu","1500").CombinedOutput();e!=nil{
        t.Fatalf("live original M4 lo MTU shrink: %v %s",e,out)
    }
    reduced,err:=os.ReadFile("/sys/class/net/lo/mtu")
    if err!=nil||string(bytes.TrimSpace(reduced))!="1500"{
        t.Fatalf("real kernel MTU did not shrink to 1500: %q %v",reduced,err)
    }
    shrinkData:=bytes.Repeat([]byte{0x6c},52)
    if n,e:=app.WriteToUDP(shrinkData,&net.UDPAddr{IP:remoteIP,Port:42001});
        e!=nil||n!=len(shrinkData){t.Fatalf("changed MTU kernel injector n=%d err=%v",n,e)}
    deadline=time.Now().Add(2*time.Second)
    failedByDriver:=false
    for time.Now().Before(deadline){
        latest,e:=b.rustOwnerLoopStats()
        if e!=nil{t.Fatalf("owner state after kernel link MTU shrink: %v",e)}
        if latest.TxErr>stats.TxErr{
            if latest.TxOK!=packets{t.Fatalf("STALE_MTU_TX_LEAK success after driver failed: %+v",latest)}
            failedByDriver=true
            break
        }
        time.Sleep(10*time.Millisecond)
    }
    if !failedByDriver{
        t.Fatalf("original M4 raw driver did not fail closed after real MTU shrink 65536→1500")
    }
    t.Logf("EMBEDDED_REAL_OWNER_MTU_CHANGE_FAIL_CLOSED_PASS old_mtu=%d new_mtu=1500 s2c_tx_ok=%d driver_reject_increased=true",
        oldMTU,stats.TxOK)
}
