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

    "github.com/lly8666/wobuzhidao/internal/linkdata"
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


// Real protected Go TLS (not a cold248 forgery) sets bit2 only in
// package-private tests; the real embedded Rust owner accepts version2
// metadata at Prepare/Commit but remains Normal/off. No FEC2 DATA enable.
func TestR0V4EmbeddedNativeProtectedFec2Bit2Scope(t *testing.T){
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(string(rune('0'+cipher)),func(t *testing.T){
            store,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
            b:=&v4EmbeddedNativeBridge{}
            c,server,ce,se:=v4PairWithPrivateBridgeCipher(
                t,b,store,cipher,true)
            if ce!=nil||se!=nil||c==nil||server==nil||!b.committed||b.handle==0{
                t.Fatalf("protected bit2 Go→original Rust private V2 scope failed %v %v",ce,se)
            }
            expected:=v4RequiredFeatures|v4FeatureFEC2
            if c.negotiatedFeatures!=expected || server.negotiatedFeatures!=expected ||
               server.verifiedCold.features!=expected {
                t.Fatal("original Go exporter-transcript feature mismatch")
            }
            phase,err:=b.state()
            if err!=nil||phase!=2{t.Fatalf("original owner not active: %d %v",phase,err)}
            if err:=b.stopRelease();err!=nil{t.Fatal(err)}
            if err:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),
                1,server.Epoch);err!=nil{t.Fatal(err)}
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
            // L01-L04: the pinned ORIGINAL Go linkdata.Fragmenter sends a
            // real previously-over-budget logical IPv4/UDP datagram as two
            // separately AEAD-protected C2S records. Rust M3 must hold the
            // first authenticated fragment without delivering any TUN bytes,
            // then reassemble exactly once into the real application socket.
            // This is not test-only Rust crypto/reassembly or a Python vector.
            originalGoFragments,err:=linkdata.NewFragmenter(maxIP)
            if err!=nil{t.Fatal(err)}
            pieces,err:=originalGoFragments.Fragment(overIP)
            if err!=nil||len(pieces)!=2{
                t.Fatalf("original Go over-budget LINK fragmenter pieces=%d err=%v",len(pieces),err)
            }
            fragmentSeq:=lastSeq+uint32(len(atWire))
            for index,piece:=range pieces{
                if len(piece)>maxIP||string(piece[:8])!="WBDLFRG1"{
                    t.Fatalf("not actual bounded original Go LINK part %d len=%d",index,len(piece))
                }
                sealed,_,sealErr:=sealer.Seal(piece)
                if sealErr!=nil||len(sealed)>int(limit){
                    t.Fatalf("original Go fragmented AEAD part %d wire=%d err=%v",
                        index,len(sealed),sealErr)
                }
                if err:=syscall.Sendto(rawfd,
                    v4RawC2STestPacket(sealed,fragmentSeq,bridge.originalFlow),0,
                    &syscall.SockaddrInet4{Addr:bridge.originalFlow.ServerIP});err!=nil{
                    t.Fatalf("original Go valid fragment kernel raw send %d: %v",index,err)
                }
                fragmentSeq+=uint32(len(sealed))
                got,failed,recvErr:=bridge.receiveRawToTun()
                if recvErr!=nil||failed!=0||got!=uint32(index){
                    t.Fatalf("real owner fragment delivery index=%d got=%d failed=%d err=%v",
                        index,got,failed,recvErr)
                }
                if index==0{
                    if err:=app.SetReadDeadline(time.Now().Add(35*time.Millisecond));err!=nil{t.Fatal(err)}
                    tmp:=make([]byte,maxIP+2)
                    n,_,readErr:=app.ReadFromUDP(tmp)
                    netErr,ok:=readErr.(net.Error)
                    if n!=0||!ok||!netErr.Timeout(){
                        t.Fatalf("premature partial-fragment TUN delivery n=%d err=%v",n,readErr)
                    }
                }
            }
            if err:=app.SetReadDeadline(time.Now().Add(2*time.Second));err!=nil{t.Fatal(err)}
            reunited:=make([]byte,maxIP+2)
            nFrag,fromFrag,readErr:=app.ReadFromUDP(reunited)
            if readErr!=nil||fromFrag==nil||!fromFrag.IP.Equal(senderIP)||
                nFrag!=len(overIP)-ipUDPHeaders||
                !bytes.Equal(reunited[:nFrag],overIP[ipUDPHeaders:]){
                t.Fatalf("real Go fragment Rust reassembly kernel UDP mismatch size=%d expected=%d err=%v",
                    nFrag,len(overIP)-ipUDPHeaders,readErr)
            }
            t.Logf("EMBEDDED_REAL_GO_FRAGMENT_RUST_TUN_REASSEMBLY_PASS suite=%d logical_ip=%d pieces=%d",
                cipher,len(overIP),len(pieces))
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
            rawDeadline:=time.Now().Add(3*time.Second)
            for attempt:=0;attempt<48&&time.Now().Before(rawDeadline);attempt++{
                buf:=make([]byte,2048)
                count,_,err:=syscall.Recvfrom(rawPeer,buf,0)
                // Real Linux netem may interrupt a blocking raw read. EINTR
                // and per-read SO_RCVTIMEO are NOT proof of packet loss;
                // keep one absolute bound and still require exact PN/seq.
                if err==syscall.EINTR||err==syscall.EAGAIN {continue}
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
            secondDeadline:=time.Now().Add(3*time.Second)
            for attempt:=0;attempt<48&&time.Now().Before(secondDeadline);attempt++{
                buf:=make([]byte,2048)
                count,_,recvErr:=syscall.Recvfrom(rawPeer,buf,0)
                if recvErr==syscall.EINTR||recvErr==syscall.EAGAIN {continue}
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
    // Make the real Linux TUN enqueue unsupported IPv6 while its original
    // IPv4 application source stays idle. The old read_ipv4_into held the
    // same mutex as authenticated writes during its next 750ms poll.
    v6addr:="fd00:241:23::1"
    if out,e:=exec.Command("ip","-6","addr","add",v6addr+"/64","dev",tunName).CombinedOutput();e!=nil{
        t.Fatalf("real TUN IPv6 test setup: %v %s",e,out)
    }
    t.Cleanup(func(){_ =exec.Command("ip","-6","addr","del",v6addr+"/64","dev",tunName).Run()})
    v6,err:=net.DialUDP("udp6",nil,&net.UDPAddr{IP:net.ParseIP("fd00:241:23::2"),Port:42005})
    if err!=nil{t.Fatalf("kernel IPv6 neighbor traffic injection: %v",err)}
    if _,err=v6.Write([]byte("unsupported-ipv6-control"));err!=nil{
        t.Fatalf("kernel IPv6 TUN write: %v",err)
    }
    _=v6.Close()
    time.Sleep(75*time.Millisecond) // bounded chance for original TX to filter IPv6
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
        if i==0 {
            // No subsequent IPv4 TUN input yet: authenticated C2S delivery
            // must not wait for the next IPv4 packet to unblock TX's reader.
            if e:=app.SetReadDeadline(time.Now().Add(400*time.Millisecond));e!=nil{t.Fatal(e)}
            got:=make([]byte,256)
            n,from,e:=app.ReadFromUDP(got)
            want:=bytes.Repeat([]byte{0x31},48)
            if e!=nil||from==nil||!from.IP.Equal(remoteIP)||!bytes.Equal(got[:n],want){
                t.Fatalf("REAL_TUN_IPV6_FILTER_BLOCKED_C2S_FIRST_DELIVERY n=%d err=%v",n,e)
            }
            t.Logf("REAL_TUN_IPV6_FILTER_C2S_UNBLOCKED_PASS delivery_before_400ms_without_new_ipv4")
        }
        if i>0 {
            down:=bytes.Repeat([]byte{0x61+byte(i)},52)
            if n,e:=app.WriteToUDP(down,&net.UDPAddr{IP:remoteIP,Port:42001});
                e!=nil||n!=len(down){t.Fatalf("S2C app injector n=%d err=%v",n,e)}
        }
    }
    for i:=1;i<packets;i++{
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
    // sendmmsg may deliver bytes before the worker's batch counter is
    // published. All original payloads were already checked above.
    // Bounded convergence ONLY for async counters, never data delivery.
    stats,e:=b.rustOwnerLoopStats()
    countDeadline:=time.Now().Add(500*time.Millisecond)
    for e==nil&&(stats.RxOK<packets||stats.TxOK<packets)&&time.Now().Before(countDeadline){
        time.Sleep(time.Millisecond)
        stats,e=b.rustOwnerLoopStats()
    }
    if e!=nil||stats.RxOK!=packets||stats.TxOK!=packets{
        t.Fatalf("original Rust live owner did not process both independent device streams: %+v %v",stats,e)
    }
    t.Logf("EMBEDDED_ORIGINAL_RUST_BACKGROUND_RX_TX_PASS C2S=%d S2C=%d threads=2 NoGoPerPacketHelpers=true errors_RX=%d errors_TX=%d",
        stats.RxOK,stats.TxOK,stats.RxErr,stats.TxErr)

    eventBefore,eventHealthy,err:=b.rustOwnerRouteEventState()
    if err!=nil||!eventHealthy{
        t.Fatalf("real netlink link observer not active: rev=%d healthy=%t err=%v",eventBefore,eventHealthy,err)
    }
    refreshBefore,err:=b.rustOwnerRouteRefreshCount()
    if err!=nil{t.Fatal(err)}
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
    // RTM_NEWLINK must invalidate BEFORE the 1s polling fallback: this is
    // a real kernel observer, not an event stub or a cached route assertion.
    eventDeadline:=time.Now().Add(750*time.Millisecond)
    eventAfter:=eventBefore
    for time.Now().Before(eventDeadline){
        current,healthy,e:=b.rustOwnerRouteEventState()
        if e!=nil||!healthy{t.Fatalf("netlink observer unavailable: %d %t %v",current,healthy,e)}
        if current>eventBefore{eventAfter=current;break}
        time.Sleep(10*time.Millisecond)
    }
    if eventAfter<=eventBefore{t.Fatalf("kernel link MTU change did not fire netlink event: initial=%d",eventBefore)}
    // Allow bounded coalescing without sleeping per packet.
    time.Sleep(110*time.Millisecond)
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
    refreshAfter,err:=b.rustOwnerRouteRefreshCount()
    if err!=nil||refreshAfter<=refreshBefore{
        t.Fatalf("netlink event did not refresh original Rust owner budget: before=%d after=%d err=%v",refreshBefore,refreshAfter,err)
    }
    t.Logf("EMBEDDED_REAL_NETLINK_ROUTE_INVALIDATION_PASS revision_before=%d revision_after=%d refresh_before=%d refresh_after=%d",eventBefore,eventAfter,refreshBefore,refreshAfter)
    t.Logf("EMBEDDED_REAL_OWNER_MTU_CHANGE_FAIL_CLOSED_PASS old_mtu=%d new_mtu=1500 s2c_tx_ok=%d driver_reject_increased=true",
        oldMTU,stats.TxOK)

    // Original real kernel TUN 1728B IP / 1700B UDP application payload:
    // its 1400B negotiated record cannot carry the single LINK frame, but
    // the *same* M1/M3 original Go-authenticated Rust TX must now fragment.
    // Independent original Go raw peer opens each real AEAD/PN and uses
    // original Go linkdata.Reassembler; no synthetic Rust bypass or mock.
    if out,e:=exec.Command("ip","link","set","dev","lo","mtu",
        strconv.Itoa(oldMTU)).CombinedOutput();e!=nil{
        t.Fatalf("restore real raw lo MTU before LINK fragments: %v %s",e,out)
    }
    if out,e:=exec.Command("ip","link","set","dev",tunName,"mtu","2000").CombinedOutput();e!=nil{
        t.Fatalf("enlarge owned real TUN ingress MTU: %v %s",e,out)
    }
    time.Sleep(200*time.Millisecond) // setup-only RTM_NEWLINK coalescing
    revised,healthy,revErr:=b.rustOwnerRouteEventState()
    if revErr!=nil||!healthy||revised<=eventAfter{
        t.Fatalf("real netlink restore/mtu events unobserved: old=%d new=%d ok=%t err=%v",
            eventAfter,revised,healthy,revErr)
    }
    beforeOversize,err:=b.rustOwnerLoopStats()
    if err!=nil{t.Fatal(err)}
    oversizedApp:=bytes.Repeat([]byte{0x7a},1700)
    if n,e:=app.WriteToUDP(oversizedApp,&net.UDPAddr{IP:remoteIP,Port:42001});
        e!=nil||n!=len(oversizedApp){
        t.Fatalf("real kernel above-LINK-budget TUN injector n=%d err=%v",n,e)
    }
    // This is the actual original Go LINK protocol, independently
    // reassembled AFTER the original S2C TLS record opener. A plaintext
    // test helper or matching Go wire arithmetic is not sufficient.
    goLink,err:=linkdata.NewReassembler(int(cLim)-31)
    if err!=nil{t.Fatal(err)}
    fragmentPN:=make(map[uint64]bool)
    var completeLarge []byte
    fragmentDeadline:=time.Now().Add(2*time.Second)
    for len(fragmentPN)<2&&time.Now().Before(fragmentDeadline){
        pkt:=make([]byte,2048)
        n,_,recvErr:=syscall.Recvfrom(peer,pkt,0)
        if recvErr!=nil{continue}
        if n<40||pkt[0]>>4!=4||pkt[9]!=6{continue}
        ihl:=int(pkt[0]&0xf)*4
        if ihl<20||ihl+20>n{continue}
        if !bytes.Equal(pkt[12:16],b.originalFlow.ServerIP[:])||
            !bytes.Equal(pkt[16:20],b.originalFlow.ClientIP[:])||
            binary.BigEndian.Uint16(pkt[ihl:ihl+2])!=b.originalFlow.ServerPort||
            binary.BigEndian.Uint16(pkt[ihl+2:ihl+4])!=b.originalFlow.ClientPort{continue}
        tcpLen:=int(pkt[ihl+12]>>4)*4
        if tcpLen<20||ihl+tcpLen>n||pkt[ihl+13]&0x08==0||n-ihl-tcpLen<=31{continue}
        rec,openErr:=open.OpenRecord(pkt[ihl+tcpLen:n])
        if openErr!=nil||rec.Kind!=tlsrecord.KindLINK{
            t.Fatalf("original Go cannot open REAL Rust fragment pn=%d err=%v",rec.PN,openErr)
        }
        if fragmentPN[rec.PN]||rec.PN<packets{
            t.Fatalf("S2C fragmented record PN repeated or rewound pn=%d",rec.PN)
        }
        fragmentPN[rec.PN]=true
        if len(rec.Payload)<=20||string(rec.Payload[:8])!="WBDLFRG1"{
            t.Fatalf("S2C real authenticated LINK fragment wire wrong pn=%d len=%d",
                rec.PN,len(rec.Payload))
        }
        reunited,done,pushErr:=goLink.Push(rec.Payload,time.Now())
        if pushErr!=nil{t.Fatalf("original Go LINK reassembler: %v",pushErr)}
        if done{
            if completeLarge!=nil{t.Fatal("duplicate fragmented business delivery")}
            completeLarge=reunited
        }
    }
    if len(fragmentPN)!=2||len(completeLarge)!=1728||
        completeLarge[0]!=0x45||completeLarge[9]!=17||
        !bytes.Equal(completeLarge[28:],oversizedApp){
        t.Fatalf("real original S2C Go peer did not reassemble 1728B IPv4: pieces=%d ip=%d",
            len(fragmentPN),len(completeLarge))
    }
    fragmentStats,err:=b.rustOwnerLoopStats()
    if err!=nil{t.Fatal(err)}
    for time.Now().Before(fragmentDeadline)&&fragmentStats.TxOK<beforeOversize.TxOK+2{
        time.Sleep(time.Millisecond)
        fragmentStats,err=b.rustOwnerLoopStats()
        if err!=nil{t.Fatal(err)}
    }
    if fragmentStats.TxOK!=beforeOversize.TxOK+2{
        t.Fatalf("S2C real M4 raw fragments not both counted: before=%+v after=%+v",
            beforeOversize,fragmentStats)
    }
    t.Logf("EMBEDDED_REAL_TUN_OVER_LINK_FRAGMENT_GO_PEER_PASS bytes=1728 fragments=2 first_delivery_once=true")
    // A small independent packet follows the large block, never waiting
    // for an old LINK gap; ordinary bytes have no LINK20 header.
    smallAfter:=bytes.Repeat([]byte{0x7b},52)
    if n,e:=app.WriteToUDP(smallAfter,&net.UDPAddr{IP:remoteIP,Port:42001});
        e!=nil||n!=len(smallAfter){
        t.Fatalf("small follower after LINK fragments n=%d err=%v",n,e)
    }
    followerDeadline:=time.Now().Add(2*time.Second)
    completed:=false
    for time.Now().Before(followerDeadline){
        got,e:=b.rustOwnerLoopStats()
        if e!=nil{t.Fatalf("owner follower stats: %v",e)}
        if got.TxOK==beforeOversize.TxOK+3{completed=true;break}
        if got.TxOK>beforeOversize.TxOK+3{
            t.Fatalf("unexpected duplicate kernel sends %+v",got)
        }
        time.Sleep(10*time.Millisecond)
    }
    if !completed{
        detail,_:=b.rustOwnerLoopStats()
        t.Fatalf("small following real large LINK not kernel-copied: before=%+v after=%+v",
            beforeOversize,detail)
    }
    t.Logf("EMBEDDED_REAL_TUN_OVER_LINK_FRAGMENT_NO_HOL_PASS fragmented=2 small=1")
    // The SAME already-running original Go TLS / Rust owner / M4 Linux
    // raw kernel/TUN path must ingest a COMPLETE legal 65535-byte IPv4 UDP
    // packet (not a synthetic 65K input or a short TUN read) and emit
    // 48 individually authenticated LINK20 fragments across >=2 owner turns.
    // The original Go peer alone decrypts, deduplicates and reassembles.
    if out,e:=exec.Command("ip","link","set","dev",tunName,"mtu","65535").CombinedOutput();e!=nil{
        t.Fatalf("actual jumbo TUN MTU setup: %v %s",e,out)
    }
    // As in the preceding 1728B test, synchronize TEST SETUP netlink/route
    // coalescing before measuring stable-link first arrival. Live MTU
    // transition races are a separate fail-closed test, never a new frame
    // stride under the same source packet ID.
    time.Sleep(200*time.Millisecond)
    if e:=syscall.SetsockoptInt(peer,syscall.SOL_SOCKET,syscall.SO_RCVBUF,2*1024*1024);e!=nil{
        t.Fatalf("raw kernel peer receive queue setup: %v",e)
    }
    jumboBefore,err:=b.rustOwnerLoopStats()
    if err!=nil{t.Fatal(err)}
    const jumboPayloadBytes=65507
    jumboPayload:=bytes.Repeat([]byte{0x5d},jumboPayloadBytes)
    if n,e:=app.WriteToUDP(jumboPayload,&net.UDPAddr{IP:remoteIP,Port:42001});
        e!=nil||n!=len(jumboPayload){
        t.Fatalf("real kernel 65535B IPv4 jumbo TUN send n=%d err=%v",n,e)
    }
    // A logically independent small app datagram must be deliverable even
    // if the 48-fragment jumbo packet is not yet reassembled at the peer.
    jumboFollower:=bytes.Repeat([]byte{0x2d},31)
    if n,e:=app.WriteToUDP(jumboFollower,&net.UDPAddr{IP:remoteIP,Port:42001});
        e!=nil||n!=len(jumboFollower){
        t.Fatalf("real kernel jumbo small follower injection n=%d err=%v",n,e)
    }
    jumboFragments:=map[uint64]bool{}
    var reassembledJumbo []byte
    expectedJumboFrames:=0
    var jumboPacketID uint32
    sawFollower:=false
    unexpectedSmall:=make([]string,0,8)
    jumboDeadline:=time.Now().Add(8*time.Second)
    for time.Now().Before(jumboDeadline) &&
        (expectedJumboFrames==0 || len(jumboFragments)<expectedJumboFrames ||
            reassembledJumbo==nil || !sawFollower){
        pkt:=make([]byte,2048)
        n,_,recvErr:=syscall.Recvfrom(peer,pkt,0)
        if recvErr!=nil{continue}
        if n<40||pkt[0]>>4!=4||pkt[9]!=6{continue}
        ihl:=int(pkt[0]&0xf)*4
        if ihl<20||ihl+20>n{continue}
        if !bytes.Equal(pkt[12:16],b.originalFlow.ServerIP[:])||
            !bytes.Equal(pkt[16:20],b.originalFlow.ClientIP[:])||
            binary.BigEndian.Uint16(pkt[ihl:ihl+2])!=b.originalFlow.ServerPort||
            binary.BigEndian.Uint16(pkt[ihl+2:ihl+4])!=b.originalFlow.ClientPort{continue}
        tcpLen:=int(pkt[ihl+12]>>4)*4
        if tcpLen<20||ihl+tcpLen>n||pkt[ihl+13]&0x08==0||n-ihl-tcpLen<=31{continue}
        rec,openErr:=open.OpenRecord(pkt[ihl+tcpLen:n])
        if openErr!=nil||rec.Kind!=tlsrecord.KindLINK{
            t.Fatalf("Go peer cannot authenticate jumbo S2C PN=%d err=%v",rec.PN,openErr)
        }
        if len(rec.Payload)>20&&string(rec.Payload[:8])=="WBDLFRG1"{
            frameCount:=int(binary.BigEndian.Uint16(rec.Payload[12:14]))
            total:=int(binary.BigEndian.Uint16(rec.Payload[14:16]))
            packetID:=binary.BigEndian.Uint32(rec.Payload[16:20])
            if frameCount<48 || frameCount>256 || total!=65535 || packetID==0 {
                t.Fatalf("invalid original Go jumbo LINK frozen header frames=%d total=%d id=%d",
                    frameCount,total,packetID)
            }
            if expectedJumboFrames==0{
                expectedJumboFrames=frameCount
                jumboPacketID=packetID
            }else if frameCount!=expectedJumboFrames || packetID!=jumboPacketID{
                t.Fatalf("mixed jumbo logical packet owner frame=%d expected=%d id=%d expectedID=%d",
                    frameCount,expectedJumboFrames,packetID,jumboPacketID)
            }
            if jumboFragments[rec.PN]{t.Fatalf("duplicate jumbo owner PN=%d",rec.PN)}
            jumboFragments[rec.PN]=true
            ready,done,pushErr:=goLink.Push(rec.Payload,time.Now())
            if pushErr!=nil{t.Fatalf("original Go jumbo LINK reassembly: %v",pushErr)}
            if done{
                if reassembledJumbo!=nil{t.Fatal("duplicated jumbo reconstructed UDP")}
                reassembledJumbo=ready
            }
        }else{
            // The earlier unrelated 52B packet may still be in the raw
            // peer queue. Only a new 31B follower proves no cross-block HOL.
            if len(rec.Payload)==28+len(jumboFollower) &&
                bytes.Equal(rec.Payload[28:],jumboFollower){
                sawFollower=true
            }else if len(unexpectedSmall)<8{
                head:=rec.Payload
                if len(head)>36{head=head[:36]}
                unexpectedSmall=append(unexpectedSmall,
                    fmt.Sprintf("pn=%d len=%d head=%x",rec.PN,len(rec.Payload),head))
            }
        }
    }
    debugStats,debugErr:=b.rustOwnerLoopStats()
    t.Logf("M0_JUMBO_REAL_KERNEL_OBSERVATION fragments=%d expected=%d reassembled=%d follower=%t raw_other=%v tx_before=%d tx_after=%d tx_error=%d stat_error=%v",
        len(jumboFragments),expectedJumboFrames,len(reassembledJumbo),sawFollower,
        unexpectedSmall,jumboBefore.TxOK,debugStats.TxOK,debugStats.TxErr,debugErr)
    if expectedJumboFrames<48 || len(jumboFragments)!=expectedJumboFrames ||
        len(reassembledJumbo)!=65535||
        !sawFollower || reassembledJumbo[0]!=0x45 ||
        binary.BigEndian.Uint16(reassembledJumbo[2:4])!=65535 ||
        reassembledJumbo[9]!=17 ||
        !bytes.Equal(reassembledJumbo[28:],jumboPayload){
        t.Fatalf("original real Go TLS Rust M4 65K jumbo failed parts=%d ip=%d follower=%t",
            len(jumboFragments),len(reassembledJumbo),sawFollower)
    }
    jumboStats,err:=b.rustOwnerLoopStats()
    jumboCountDeadline:=time.Now().Add(500*time.Millisecond)
    for err==nil && jumboStats.TxOK<jumboBefore.TxOK+uint64(expectedJumboFrames+1)&&
        time.Now().Before(jumboCountDeadline){
        time.Sleep(time.Millisecond)
        jumboStats,err=b.rustOwnerLoopStats()
    }
    if err!=nil||jumboStats.TxOK!=jumboBefore.TxOK+uint64(expectedJumboFrames+1){
        t.Fatalf("original owner 48 jumbo +1 independent kernel copies: before=%+v after=%+v err=%v",
            jumboBefore,jumboStats,err)
    }
    t.Logf("EMBEDDED_REAL_GO_TLS_RUST_M4_TUN_65535_CROSS_TURN_LINK_NOHOL_PASS ipv4=%d fragments=%d fragment_count_ge_48=1 follower=1 original_AEAD_PN=1 native_M4_sendmmsg=1",
        len(reassembledJumbo),len(jumboFragments))
    // Force a REAL 65KiB packet to pause precisely after its first
    // kernel-copied <=32-frame M4 batch. Change the actual kernel TUN link
    // revision while the other 19 original LINK frames have not been sealed.
    // There is no synthetic prefix/error injector in this test.
    pauseStatus,_,err:=b.rustOwnerDebugJumboPause(true)
    if err!=nil||pauseStatus {t.Fatalf("arm original kernel pause: %t %v",pauseStatus,err)}
    defer func(){_,_,_=b.rustOwnerDebugJumboPause(false)}()
    midflightBefore,err:=b.rustOwnerLoopStats()
    if err!=nil{t.Fatal(err)}
    midflightRevision,healthy,err:=b.rustOwnerRouteEventState()
    if err!=nil||!healthy{t.Fatalf("midflight kernel route watcher: %d %t %v",midflightRevision,healthy,err)}
    if n,e:=app.WriteToUDP(jumboPayload,&net.UDPAddr{IP:remoteIP,Port:42001});
        e!=nil||n!=len(jumboPayload){
        t.Fatalf("second real kernel 65KiB in-flight source: n=%d err=%v",n,e)
    }
    paused:=false
    midflightLoans:=uint32(0)
    for lim:=time.Now().Add(3*time.Second);time.Now().Before(lim);{
        var e error
        paused,midflightLoans,e=b.rustOwnerDebugJumboPause(true)
        if e!=nil{t.Fatalf("real midflight barrier error: %v",e)}
        if paused{break}
        time.Sleep(time.Millisecond)
    }
    if !paused||midflightLoans!=0{
        t.Fatalf("original kernel <=32 turn not quiescent: paused=%t loans=%d",paused,midflightLoans)
    }
    midflightFirst,err:=b.rustOwnerLoopStats()
    if err!=nil||midflightFirst.TxOK!=midflightBefore.TxOK+32{
        t.Fatalf("original native first 32 kernel-copied frames incomplete: before=%+v after=%+v err=%v",
            midflightBefore,midflightFirst,err)
    }
    if out,e:=exec.Command("ip","link","set","dev",tunName,"mtu","65534").CombinedOutput();e!=nil{
        t.Fatalf("live in-flight TUN MTU -1 mutation: %v %s",e,out)
    }
    witnessed:=false
    for lim:=time.Now().Add(750*time.Millisecond);time.Now().Before(lim);{
        rev,ok,e:=b.rustOwnerRouteEventState()
        if e!=nil||!ok{t.Fatalf("in-flight route event watcher unhealthy rev=%d err=%v",rev,e)}
        if rev>midflightRevision{witnessed=true;break}
        time.Sleep(time.Millisecond)
    }
    if !witnessed{t.Fatal("no real netlink route revision while original 65KiB packet paused")}
    if _,_,e:=b.rustOwnerDebugJumboPause(false);e!=nil{t.Fatal(e)}
    // This bounded wait is test observation for an already-triggered real
    // event, not an extra batch fill timer in the production owner.
    time.Sleep(200*time.Millisecond)
    midflightAfter,err:=b.rustOwnerLoopStats()
    if err!=nil||midflightAfter.TxOK!=midflightFirst.TxOK{
        t.Fatalf("old packet ID tail sent after true kernel MTU change: first=%+v after=%+v err=%v",
            midflightFirst,midflightAfter,err)
    }
    // The unrelated packet after abandoning the 65KiB old-ID tail must
    // still reach real M4 raw/TCP; restore input MTU for existing next gate.
    if out,e:=exec.Command("ip","link","set","dev",tunName,"mtu","65535").CombinedOutput();e!=nil{
        t.Fatalf("restore TUN MTU for independent following packet: %v %s",e,out)
    }
    time.Sleep(200*time.Millisecond)
    midflightFollower:=bytes.Repeat([]byte{0x53},37)
    if n,e:=app.WriteToUDP(midflightFollower,&net.UDPAddr{IP:remoteIP,Port:42001});e!=nil||n!=len(midflightFollower){
        t.Fatalf("midflight aborted jumbo follower source n=%d err=%v",n,e)
    }
    foundMidflightFollower:=false
    var abandonedID uint32
    var abandonedParts int
    for lim:=time.Now().Add(4*time.Second);time.Now().Before(lim)&&!foundMidflightFollower;{
        pkt:=make([]byte,2048)
        n,_,e:=syscall.Recvfrom(peer,pkt,0)
        if e!=nil||n<40||pkt[0]>>4!=4||pkt[9]!=6{continue}
        ihl:=int(pkt[0]&0xf)*4
        if ihl<20||ihl+20>n||!bytes.Equal(pkt[12:16],b.originalFlow.ServerIP[:])||
            !bytes.Equal(pkt[16:20],b.originalFlow.ClientIP[:]){continue}
        if binary.BigEndian.Uint16(pkt[ihl:ihl+2])!=b.originalFlow.ServerPort||
            binary.BigEndian.Uint16(pkt[ihl+2:ihl+4])!=b.originalFlow.ClientPort{continue}
        tcpLen:=int(pkt[ihl+12]>>4)*4
        if tcpLen<20||ihl+tcpLen>n||pkt[ihl+13]&0x08==0||n-ihl-tcpLen<=31{continue}
        rec,e:=open.OpenRecord(pkt[ihl+tcpLen:n])
        if e!=nil||rec.Kind!=tlsrecord.KindLINK{t.Fatalf("midflight real Go AEAD: %v",e)}
        if len(rec.Payload)>20&&string(rec.Payload[:8])=="WBDLFRG1"{
            id:=binary.BigEndian.Uint32(rec.Payload[16:20])
            if abandonedID==0{abandonedID=id}
            if id!=abandonedID{t.Fatalf("mixed old-ID midflight frames: %d != %d",id,abandonedID)}
            abandonedParts++
            if abandonedParts>32{t.Fatal("old 65KiB packet emitted tail after route event")}
        }else if len(rec.Payload)==28+len(midflightFollower)&&
            bytes.Equal(rec.Payload[28:],midflightFollower){
            foundMidflightFollower=true
        }
    }
    if !foundMidflightFollower||abandonedParts!=32{
        t.Fatalf("real midflight abort lost healthy follower or incomplete initial prefix: parts=%d follower=%t",abandonedParts,foundMidflightFollower)
    }
    t.Logf("EMBEDDED_REAL_JUMBO_MIDFLIGHT_MTU_ABORT_NO_TAIL_PASS copied_prefix=32 sealed_tail=0 old_id_parts=%d loans=%d original_M4_kernel=1 real_netlink=1 follower=1",
        abandonedParts,midflightLoans)

    // Live original Linux netlink TUN MTU -1 after the complete jumbo:
    // the next independent small packet cannot be consumed and dropped
    // merely because owner route refresh is in its short defer window.
    // It is NOT a claim that an in-flight jumbo may change fragment stride.
    mtuEventBefore,healthy,err:=b.rustOwnerRouteEventState()
    if err!=nil||!healthy{t.Fatalf("before real TUN MTU-1 race event: %d %t %v",mtuEventBefore,healthy,err)}
    beforeRouteFollower,err:=b.rustOwnerLoopStats()
    if err!=nil{t.Fatal(err)}
    if out,e:=exec.Command("ip","link","set","dev",tunName,"mtu","65534").CombinedOutput();e!=nil{
        t.Fatalf("real TUN -1 MTU link event setup: %v %s",e,out)
    }
    racedFollower:=bytes.Repeat([]byte{0x4e},29)
    if n,e:=app.WriteToUDP(racedFollower,&net.UDPAddr{IP:remoteIP,Port:42001});
        e!=nil||n!=len(racedFollower){
        t.Fatalf("TUN MTU -1 follower injection n=%d err=%v",n,e)
    }
    afterEventRev:=mtuEventBefore
    for lim:=time.Now().Add(750*time.Millisecond);time.Now().Before(lim);{
        now,ok,e:=b.rustOwnerRouteEventState()
        if e!=nil||!ok{t.Fatalf("live TUN event watcher unhealthy rev=%d err=%v",now,e)}
        if now>mtuEventBefore{afterEventRev=now;break}
        time.Sleep(5*time.Millisecond)
    }
    if afterEventRev<=mtuEventBefore{
        t.Fatalf("kernel TUN MTU -1 did not deliver real netlink event rev=%d",mtuEventBefore)
    }
    receivedRouteFollower:=false
    for lim:=time.Now().Add(3*time.Second);time.Now().Before(lim) && !receivedRouteFollower;{
        pkt:=make([]byte,2048)
        n,_,recvErr:=syscall.Recvfrom(peer,pkt,0)
        if recvErr!=nil||n<40||pkt[0]>>4!=4||pkt[9]!=6{continue}
        ihl:=int(pkt[0]&0xf)*4
        if ihl<20||ihl+20>n{continue}
        if !bytes.Equal(pkt[12:16],b.originalFlow.ServerIP[:])||
            !bytes.Equal(pkt[16:20],b.originalFlow.ClientIP[:])||
            binary.BigEndian.Uint16(pkt[ihl:ihl+2])!=b.originalFlow.ServerPort||
            binary.BigEndian.Uint16(pkt[ihl+2:ihl+4])!=b.originalFlow.ClientPort{continue}
        tcpLen:=int(pkt[ihl+12]>>4)*4
        if tcpLen<20||ihl+tcpLen>n||pkt[ihl+13]&0x08==0||n-ihl-tcpLen<=31{continue}
        opened,e:=open.OpenRecord(pkt[ihl+tcpLen:n])
        if e!=nil||opened.Kind!=tlsrecord.KindLINK{
            t.Fatalf("MTU -1 netlink follower Go original AEAD: pn=%d err=%v",opened.PN,e)
        }
        if len(opened.Payload)==28+len(racedFollower) &&
            bytes.Equal(opened.Payload[28:],racedFollower){
            receivedRouteFollower=true
        }
    }
    afterRouteFollower,err:=b.rustOwnerLoopStats()
    if err!=nil||!receivedRouteFollower||
        afterRouteFollower.TxOK!=beforeRouteFollower.TxOK+1||
        afterRouteFollower.TxErr>beforeRouteFollower.TxErr+5{
        t.Fatalf("real TUN MTU -1 follower HOL/error loop failure delivered=%t before=%+v after=%+v err=%v",
            receivedRouteFollower,beforeRouteFollower,afterRouteFollower,err)
    }
    t.Logf("EMBEDDED_REAL_TUN_MTU_MINUS1_FOLLOWER_NOHOL_PASS before=%d after=%d copied=1 owner_tx_error_growth=%d",
        mtuEventBefore,afterEventRev,afterRouteFollower.TxErr-beforeRouteFollower.TxErr)
    // One more fresh full-size ORIGINAL kernel TUN packet, this time
    // interrupted by REAL Stop/Release after the first 32 sendmmsg copies.
    // The barrier is test-only and outside all owner/device locks. No
    // synthetic packet numbers, driver completions or alternate sender.
    if out,e:=exec.Command("ip","link","set","dev",tunName,"mtu","65535").CombinedOutput();e!=nil{
        t.Fatalf("restore real TUN 65K ingress before midflight Stop: %v %s",e,out)
    }
    time.Sleep(200*time.Millisecond)
    if _,_,e:=b.rustOwnerDebugJumboPause(true);e!=nil{
        t.Fatalf("arm real 65K Stop barrier: %v",e)
    }
    beforeStop,err:=b.rustOwnerLoopStats()
    if err!=nil{t.Fatal(err)}
    if n,e:=app.WriteToUDP(jumboPayload,&net.UDPAddr{IP:remoteIP,Port:42001});
        e!=nil||n!=len(jumboPayload){
        t.Fatalf("real kernel 65K Stop source n=%d err=%v",n,e)
    }
    stopPaused:=false
    var stopLoans uint32
    for lim:=time.Now().Add(3*time.Second);time.Now().Before(lim);{
        var e error
        stopPaused,stopLoans,e=b.rustOwnerDebugJumboPause(true)
        if e!=nil{t.Fatalf("midflight Stop ownership status: %v",e)}
        if stopPaused{break}
        time.Sleep(time.Millisecond)
    }
    if !stopPaused||stopLoans!=0{
        t.Fatalf("actual original M1 loan not quiescent before kernel Stop: paused=%t loans=%d",stopPaused,stopLoans)
    }
    duringStop,e:=b.rustOwnerLoopStats()
    if e!=nil||duringStop.TxOK!=beforeStop.TxOK+32{
        t.Fatalf("real first 32 kernel copies not completed before Stop: before=%+v during=%+v err=%v",beforeStop,duringStop,e)
    }
    // Stop must wake the paused worker, join both original Rust threads and
    // retire the SAME native M4 raw/TUN drivers before returning to Go.
    if e:=b.stopRelease();e!=nil{
        t.Fatalf("actual midflight 65K original owner Stop/Release: %v",e)
    }
    stopParts:=0
    var stopID uint32
    stopDeadline:=time.Now().Add(650*time.Millisecond)
    for time.Now().Before(stopDeadline){
        pkt:=make([]byte,2048)
        n,_,e:=syscall.Recvfrom(peer,pkt,0)
        if e!=nil||n<40||pkt[0]>>4!=4||pkt[9]!=6{continue}
        ihl:=int(pkt[0]&0xf)*4
        if ihl<20||ihl+20>n||!bytes.Equal(pkt[12:16],b.originalFlow.ServerIP[:])||
            !bytes.Equal(pkt[16:20],b.originalFlow.ClientIP[:]){continue}
        if binary.BigEndian.Uint16(pkt[ihl:ihl+2])!=b.originalFlow.ServerPort||
            binary.BigEndian.Uint16(pkt[ihl+2:ihl+4])!=b.originalFlow.ClientPort{continue}
        tcpLen:=int(pkt[ihl+12]>>4)*4
        if tcpLen<20||ihl+tcpLen>n||pkt[ihl+13]&0x08==0||n-ihl-tcpLen<=31{continue}
        rec,e:=open.OpenRecord(pkt[ihl+tcpLen:n])
        if e!=nil||rec.Kind!=tlsrecord.KindLINK{
            t.Fatalf("midflight Stop original Go AEAD/PN verification: %v",e)
        }
        if len(rec.Payload)<=20||string(rec.Payload[:8])!="WBDLFRG1"{
            t.Fatalf("nonfragment sent after original jumbo Stop: pn=%d",rec.PN)
        }
        id:=binary.BigEndian.Uint32(rec.Payload[16:20])
        if stopID==0{stopID=id}
        if id!=stopID{t.Fatalf("old generation mixed LINK packet after Stop id=%d expected=%d",id,stopID)}
        stopParts++
        if stopParts>32{t.Fatalf("late old-ID tail after real Stop: parts=%d",stopParts)}
    }
    if stopID==0||stopParts!=32{
        t.Fatalf("real Stop did not preserve exact first kernel prefix: ID=%d fragments=%d",stopID,stopParts)
    }
    t.Logf("EMBEDDED_REAL_JUMBO_MIDFLIGHT_STOP_NO_TAIL_PASS copied_prefix=32 old_id_parts=%d remaining_sent=0 loans=%d join=1 original_M4_kernel=1",stopParts,stopLoans)
    if e:=b.startRustOwnerLoop(uint32(lo.Index));e==nil{
        t.Fatal("retired original Go-authenticated Rust session restarted")
    }
    t.Log("EMBEDDED_REAL_ACTIVE_WORKERS_STOP_RELEASE_NO_RESTART_PASS")
}
