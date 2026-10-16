//go:build linux && cgo && wbd_v4_native_probe

package realityfront
import ("errors";"testing";"hash/fnv";"fmt";"bytes";"encoding/binary";"github.com/lly8666/wobuzhidao/internal/tlsrecord";"github.com/lly8666/wobuzhidao/internal/faketcp";"net";"time";"runtime";"os";"os/exec";"syscall";"unsafe")

// Actual Go protected TLS reaches Rust's independent fresh ScopedOwner using
// the package-private Prepare/Detach/Commit hook; production still disabled.
func TestR0V4NativeRustProbeActualProtectedFreshOwner(t *testing.T){
    store,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
    var first uint64
    var stillBorrowed *v4NativeRustProbe
    for i:=0;i<2;i++{
        b:=&v4NativeRustProbe{}
        if i==0 {
            // Real FakeTCP packets queued after Prepare and before protected
            // reply, then delivered from real Detach to Rust-owned RX slabs.
            b.injectEarly=[][]byte{{0x01,0x41,0x45,0x41,0x44}, {0x02,0x46,0x45,0x43}}
        }
        c,s,ce,se:=v4PairWithPrivateBridge(t,b,store)
        if ce!=nil||se!=nil||c==nil||s==nil{
            t.Fatalf("real protected TLS %d: client=%v server=%v",i,ce,se)
        }
        if !b.prepared||!b.committed||b.handle==0{t.Fatal("no fresh Rust candidate")}
        if phase,e:=b.state();e!=nil||phase!=2{
            t.Fatalf("Rust owner not committed after Go detach: phase=%d err=%v",phase,e)
        }
        if i==1 && b.handle==first{t.Fatal("Rust generation reused")}
        var count,size uint32
        var digest uint64
        if i==0 {
            count,size,digest,err=b.holdEarly()
        } else {
            count,size,digest,err=b.drainEarly()
        }
        if err!=nil{t.Fatal(err)}
        gohash:=fnv.New64a()
        var goSize int
        for _,p:=range s.EarlyRecords{
            goSize+=len(p.Payload)
            if _,e:=gohash.Write(p.Payload);e!=nil{t.Fatal(e)}
        }
        if count!=uint32(len(s.EarlyRecords))||size!=uint32(goSize)||digest!=gohash.Sum64(){
            t.Fatalf("Go Detach bytes not physically Rust-owned: n=%d/%d bytes=%d/%d hash=%x/%x",
                count,len(s.EarlyRecords),size,goSize,digest,gohash.Sum64())
        }
        if i==0 && count!=2{t.Fatal("injected real transition packets never crossed Rust FFI")}
        if _,_,_,e:=b.drainEarly();e==nil{t.Fatal("duplicate Rust early drain allowed")}
        if i==0{first=b.handle}
        cc,ce:=c.ColdSnapshot();ss,se:=s.ColdSnapshot()
        if ce!=nil||se!=nil||cc.Epoch()!=ss.Epoch()||
            cc.DirectionKeys()!=ss.DirectionKeys(){
            t.Fatal("in-process Rust candidate not sourced from true Go TLS")
        }
        if i==0 {
            pending,e:=b.stopPending()
            if e!=nil||!pending{t.Fatalf("Stop must stay incomplete while RX borrowed: %v %v",pending,e)}
            if phase,e:=b.state();e!=nil||phase!=4{
                t.Fatalf("incomplete Stop lost retirement state: %d %v",phase,e)
            }
            if e:=b.stopAndRelease();e==nil{
                t.Fatal("released Rust generation while RX driver still borrowed")
            }
            stillBorrowed=b // old slab remains alive while next Go TLS creates a NEW Rust owner
        } else {
            if e:=b.stopAndRelease();e!=nil{t.Fatal(e)}
            if _,e:=b.state();!errors.Is(e,errV4NativeProbe){
                t.Fatal("released Rust generation still addressable")
            }
        }
        if e:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,s.Epoch);e!=nil{
            t.Fatal(e)
        }
    }
    if stillBorrowed==nil{t.Fatal("no prior Rust loan held across fresh Go TLS")}
    if e:=stillBorrowed.returnHeld();e!=nil{t.Fatal(e)}
    if e:=stillBorrowed.returnHeld();e==nil{t.Fatal("double return of old RX loan")}
    if pending,e:=stillBorrowed.stopPending();e!=nil||pending{
        t.Fatalf("old scoped Stop did not quiesce after loan return: %v %v",pending,e)
    }
    if e:=stillBorrowed.stopAndRelease();e!=nil{t.Fatal(e)}
    if _,e:=stillBorrowed.state();!errors.Is(e,errV4NativeProbe){
        t.Fatal("old generation visible after final lease return")
    }
    b:=&v4NativeRustProbe{}
    if _,e:=b.prepare(V4ColdSessionSnapshot{},0,v4PeerTransport{});e==nil{
        t.Fatal("forged empty snapshot minted Rust owner candidate")
    }
}

 
// Actual credential-checked Go V4 all-cipher sessions install the SAME
// normal-build Rust crypto state that eventual RX ingress must use.
// This does not claim a business receiver/production capability or kernel I/O.
func TestR0V4NativeRustProtectedAEADReplayAllCiphers(t *testing.T){
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(fmt.Sprintf("cipher-%d",cipher),func(t *testing.T){
            store,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
            bridge:=&v4NativeRustProbe{}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,bridge,store,cipher)
            if ce!=nil||se!=nil||client==nil||server==nil||!bridge.committed{
                t.Fatalf("protected Go session not committed: %v %v",ce,se)
            }
            clientCold,e:=client.ColdSnapshot();if e!=nil{t.Fatal(e)}
            cold,e:=server.ColdSnapshot();if e!=nil{t.Fatal(e)}
            if cold.DirectionKeys()!=clientCold.DirectionKeys()||cold.Cipher()!=cipher{
                t.Fatal("Rust crypto source was not protected negotiated direction")
            }
            cLimit,sLimit:=cold.RecordLimits()
            send,e:=tlsrecord.NewSealerForCipher(cold.DirectionKeys().C2S,int(sLimit),cipher)
            if e!=nil{t.Fatal(e)}
            samples:=[][]byte{[]byte("pn0"),[]byte("pn1"),[]byte("pn2")}
            var wires [3][]byte
            for i,payload:=range samples{
                raw,pn,e:=send.Seal(payload)
                if e!=nil||pn!=uint64(i){t.Fatalf("Go PN seal %d: %d %v",i,pn,e)}
                wires[i]=raw
            }
            for _,idx:=range []int{2,0,1}{
                pn,kind,digest,e:=bridge.openAuthenticated(wires[idx])
                h:=fnv.New64a();_,_=h.Write(samples[idx])
                if e!=nil||pn!=uint64(idx)||kind!=0||digest!=h.Sum64(){
                    t.Fatalf("real Rust unique out-of-order open %d: pn=%d kind=%d hash=%x err=%v",
                        idx,pn,kind,digest,e)
                }
            }
            if _,_,_,e:=bridge.openAuthenticated(wires[0]);e==nil{
                t.Fatal("verified old PN replay delivered twice")
            }
            corrupt:=append([]byte(nil),wires[1]...)
            corrupt[len(corrupt)-1]^=0x80
            if _,_,_,e:=bridge.openAuthenticated(corrupt);e==nil{
                t.Fatal("corrupted AEAD record was accepted")
            }
            opposite,e:=tlsrecord.NewSealerForCipher(cold.DirectionKeys().S2C,int(cLimit),cipher)
            if e!=nil{t.Fatal(e)}
            wrong,_,e:=opposite.Seal([]byte("wrong-direction"))
            if e!=nil{t.Fatal(e)}
            if _,_,_,e:=bridge.openAuthenticated(wrong);e==nil{
                t.Fatal("TX-direction keys accepted by Rust RX")
            }
            // The same real RX queue can authenticate control-kind records,
            // but MUST NOT send them to the LINK/business callback.
            health,_,e:=send.SealHealth([]byte("health-not-business"))
            if e!=nil{t.Fatal(e)}
            if _,_,_,e:=bridge.openAuthenticated(health);e==nil{
                t.Fatal("authenticated Health escaped via LINK delivery callback")
            }
            if e:=bridge.stopAndRelease();e!=nil{t.Fatal(e)}
            if _,_,_,e:=bridge.openAuthenticated(wires[2]);e==nil{
                t.Fatal("Stop allowed old generation to open another record")
            }
            if e:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);e!=nil{
                t.Fatal(e)
            }
        })
    }
}


// Produces the pinned legacy LINK20 wire layout for a Go-side *test input*.
// This only creates encrypted stimulus; there is no separate Go receiver,
// alternate crypto, owner activation or application delivery implementation.
func v4TestLegacyLinkFrames(payload []byte,mtu int,id uint32)[][]byte{
    if mtu<=20||len(payload)<=mtu||len(payload)>65535||id==0 {panic("bad LINK test case")}
    chunk:=mtu-20
    count:=(len(payload)+chunk-1)/chunk
    frames:=make([][]byte,0,count)
    for i,pos:=0,0;pos<len(payload);i,pos=i+1,pos+chunk{
        end:=pos+chunk
        if end>len(payload){end=len(payload)}
        frame:=make([]byte,20+end-pos)
        copy(frame[:8],[]byte("WBDLFRG1"))
        frame[8]=1
        binary.BigEndian.PutUint16(frame[10:12],uint16(i))
        binary.BigEndian.PutUint16(frame[12:14],uint16(count))
        binary.BigEndian.PutUint16(frame[14:16],uint16(len(payload)))
        binary.BigEndian.PutUint32(frame[16:20],id)
        copy(frame[20:],payload[pos:end])
        frames=append(frames,frame)
    }
    return frames
}

// All three real Go TLS suite keys pass the SAME normal-build Rust
// ScopedOwner loan -> AEAD/PN -> M3 LINK parser/reassembly -> complete packet
// callback. This is not yet a TUN/raw driver or a product application sink.
func TestR0V4NativeRustProtectedNormalOffLinkFirstPacket(t *testing.T){
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(fmt.Sprintf("cipher-%d",cipher),func(t *testing.T){
            store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
            bridge:=&v4NativeRustProbe{}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,bridge,store,cipher)
            if ce!=nil||se!=nil||client==nil||server==nil||!bridge.committed{
                t.Fatalf("protected TLS/owner not installed %v %v",ce,se)
            }
            cold,e:=server.ColdSnapshot();if e!=nil{t.Fatal(e)}
            _,limit:=cold.RecordLimits()
            effectiveLinkCeiling:=int(limit)-31
            if effectiveLinkCeiling<=20{t.Fatal("invalid negotiated test wire ceiling")}
            seal,e:=tlsrecord.NewSealerForCipher(cold.DirectionKeys().C2S,int(limit),cipher)
            if e!=nil{t.Fatal(e)}
            // First fragment missing: independently complete packet must
            // arrive immediately, without HOL or FEC/repair waiting.
            whole:=bytes.Repeat([]byte{0x5a},effectiveLinkCeiling+1)
            frames:=v4TestLegacyLinkFrames(whole,effectiveLinkCeiling,1)
            if len(frames)!=2{t.Fatal("wrong legacy LINK fragment count")}
            tail,tailPN,e:=seal.Seal(frames[1]);if e!=nil||tailPN!=0{t.Fatalf("seal tail %d %v",tailPN,e)}
            if _,_,_,e=bridge.openAuthenticated(tail);!errors.Is(e,errV4NativeLinkPending){
                t.Fatalf("incomplete authenticated fragment escaped into business: %v",e)
            }
            fresh:=[]byte("new-normal-off-first-arrival")
            freshWire,freshPN,e:=seal.Seal(fresh)
            if e!=nil||freshPN!=1{t.Fatalf("seal fresh %d %v",freshPN,e)}
            gotPN,kind,gotHash,e:=bridge.openAuthenticated(freshWire)
            expected:=fnv.New64a();_,_=expected.Write(fresh)
            if e!=nil||gotPN!=freshPN||kind!=0||gotHash!=expected.Sum64(){
                t.Fatalf("independent NORMAL first packet blocked: pn=%d digest=%x want=%x err=%v",
                    gotPN,gotHash,expected.Sum64(),e)
            }
            head,headPN,e:=seal.Seal(frames[0])
            if e!=nil||headPN!=2{t.Fatalf("seal head %d %v",headPN,e)}
            gotPN,kind,gotHash,e=bridge.openAuthenticated(head)
            expected=fnv.New64a();_,_=expected.Write(whole)
            if e!=nil||gotPN!=headPN||kind!=0||gotHash!=expected.Sum64(){
                t.Fatalf("complete LINK reassembly not delivered once: pn=%d digest=%x want=%x err=%v",
                    gotPN,gotHash,expected.Sum64(),e)
            }
            // A new authenticated PN carrying the same retired LINK packet
            // ID must not cause a second application delivery.
            replayWire,_,e:=seal.Seal(frames[0]);if e!=nil{t.Fatal(e)}
            if _,_,_,e=bridge.openAuthenticated(replayWire);e==nil{
                t.Fatal("retired completed LINK packet delivered again")
            }
            // AEAD-valid but malformed LINK framing also cannot escape.
            invalid:=append([]byte(nil),frames[0]...)
            invalid[9]=1
            invalidWire,_,e:=seal.Seal(invalid);if e!=nil{t.Fatal(e)}
            if _,_,_,e=bridge.openAuthenticated(invalidWire);e==nil{
                t.Fatal("malformed authenticated LINK packet delivered")
            }
            if _,_,_,e=bridge.openAuthenticated(head);e==nil{
                t.Fatal("duplicate PN delivered after finished packet")
            }
            if e:=bridge.stopAndRelease();e!=nil{t.Fatal(e)}
            if _,_,_,e=bridge.openAuthenticated(freshWire);e==nil{
                t.Fatal("retired owner delivered old business after Stop")
            }
            if e:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);e!=nil{
                t.Fatal(e)
            }
        })
    }
}


// Bidirectional V4 test source: the S2C half is sealed by NORMAL-BUILD Rust
// LaneTxCrypto, published through M1's actual ScopedOwner TxOwner fresh queue
// as immutable FrozenRecord and read inside a generation-fenced ready batch;
// the existing Go TLS-derived Opener independently authenticates its bytes.
// The C2S half still traverses the same Rust ScopedOwner RX and M3 reassembly.
func TestR0V4NativeRustProtectedNormalOffBidirectionalScopedFirst(t *testing.T){
    for _,suite:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(fmt.Sprintf("cipher-%d",suite),func(t *testing.T){
            bridge:=&v4NativeRustProbe{}
            if _,_,_,e:=bridge.sealNativeNormal([]byte("before-detach"),1200,faketcp.DefaultMSS);e==nil{
                t.Fatal("TX admitted without Go's protected reply and Detach")
            }
            store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,bridge,store,suite)
            if ce!=nil||se!=nil||client==nil||server==nil||!bridge.committed{
                t.Fatalf("protected TLS owner failed: %v %v",ce,se)
            }
            if bridge.peerMSS!=faketcp.DefaultMSS||!bridge.peerAdvertised{
                t.Fatalf("SYN profile was not bound to real Go V4 association: mss=%d advertised=%v",bridge.peerMSS,bridge.peerAdvertised)
            }
            serverCold,e:=server.ColdSnapshot();if e!=nil{t.Fatal(e)}
            clientCold,e:=client.ColdSnapshot();if e!=nil{t.Fatal(e)}
            if serverCold.DirectionKeys()!=clientCold.DirectionKeys(){
                t.Fatal("V4 Go TLS exporter direction mismatch")
            }
            cLimit,sLimit:=serverCold.RecordLimits()
            recv,e:=tlsrecord.NewOpenerForCipher(
                clientCold.DirectionKeys().S2C,int(cLimit),suite)
            if e!=nil{t.Fatal(e)}
            goSend,e:=tlsrecord.NewSealerForCipher(
                clientCold.DirectionKeys().C2S,int(sLimit),suite)
            if e!=nil{t.Fatal(e)}
            // These are SYNTHETIC path input values for test only; the
            // production M4 PathBudget/actual MSS still remain NOT_RUN.
            first:=[]byte{0x00,0x51,0xff,0x00,0x61}
            wire,pn,seq,e:=bridge.sealNativeNormal(first,1200,faketcp.DefaultMSS)
            if e!=nil||pn!=0||seq!=bridge.txBoundary{
                t.Fatalf("Rust first TX PN/boundary wrong: pn=%d seq=%d want=%d err=%v",
                    pn,seq,bridge.txBoundary,e)
            }
            opened,e:=recv.OpenRecord(wire)
            if e!=nil||opened.PN!=pn||opened.Kind!=tlsrecord.KindLINK||
                !bytes.Equal(opened.Payload,first){
                t.Fatalf("Go client failed to authenticate Rust S2C first packet: %+v err=%v",opened,e)
            }
            // Explicit budget guard rejects a too-small carrier and any
            // raw ordinary payload that requires LINK magic escaping.
            if _,_,_,e:=bridge.sealNativeNormal(bytes.Repeat([]byte{1},128),1200,64);e==nil{
                t.Fatal("caller attempted to replace observed SYN MSS")
            }
            // MTU1500 would allow 1460 TCP payload, but the REAL observed
            // SYN MSS1360 prevents a 1340B ordinary payload + 31B record.
            if _,_,_,e:=bridge.sealNativeNormal(bytes.Repeat([]byte{1},1340),1500,faketcp.DefaultMSS);e==nil{
                t.Fatal("Rust TX ignored original SYN's peer MSS bound")
            }
            if _,_,_,e:=bridge.sealNativeNormal([]byte("WBDLFRG1needs-escape"),1200,faketcp.DefaultMSS);e==nil{
                t.Fatal("Rust TX published unescaped magic-prefixed LINK")
            }
            second:=[]byte("server-normal-fec-off-second")
            wire2,pn2,seq2,e:=bridge.sealNativeNormal(second,1200,faketcp.DefaultMSS)
            if e!=nil||pn2!=pn+1||seq2!=seq+uint32(len(wire)){
                t.Fatalf("Rust TX sequence/PN reused: %v pn=%d seq=%d",e,pn2,seq2)
            }
            opened2,e:=recv.OpenRecord(wire2)
            if e!=nil||opened2.PN!=pn2||!bytes.Equal(opened2.Payload,second){
                t.Fatalf("Go client Rust S2C second packet mismatch: %+v err=%v",opened2,e)
            }
            // Go C2S to the very same Rust owner RX path, not an
            // independent decryptor or test-only delivery queue.
            c2s:=[]byte("client-normal-fec-off-first")
            cwire,_,e:=goSend.Seal(c2s);if e!=nil{t.Fatal(e)}
            gotpn,kind,digest,e:=bridge.openAuthenticated(cwire)
            want:=fnv.New64a();_,_=want.Write(c2s)
            if e!=nil||gotpn!=0||kind!=0||digest!=want.Sum64(){
                t.Fatalf("Go C2S into Rust owner first packet failed: %v pn=%d",e,gotpn)
            }
            if e:=bridge.stopAndRelease();e!=nil{t.Fatal(e)}
            if _,_,_,e:=bridge.sealNativeNormal([]byte("after-stop"),1200,faketcp.DefaultMSS);e==nil{
                t.Fatal("retired scoped owner allowed S2C TX")
            }
            if e:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);e!=nil{t.Fatal(e)}
        })
    }
}

func TestR0V4NativeRustLinuxKernelBudget(t *testing.T){
    iface,err:=net.InterfaceByName("lo")
    if err!=nil||iface==nil||iface.Index<=0||iface.MTU<576 {
        t.Fatalf("local Linux kernel interface: %v",err)
    }
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(fmt.Sprintf("suite-%d",cipher),func(t *testing.T){
            store,_:=NewV4EpochStore(1)
            bridge:=&v4NativeRustProbe{}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,bridge,store,cipher)
            if ce!=nil||se!=nil||client==nil||server==nil||!bridge.committed{
                t.Fatalf("V4 protected session: %v %v",ce,se)
            }
            cold,e:=client.ColdSnapshot();if e!=nil{t.Fatal(e)}
            limit,_:=cold.RecordLimits()
            opener,e:=tlsrecord.NewOpenerForCipher(cold.DirectionKeys().S2C,int(limit),cipher)
            if e!=nil{t.Fatal(e)}
            if _,_,_,e=bridge.sealNativeNormalObservedLinux([]byte("wrong"),0);e==nil{
                t.Fatal("missing kernel interface scope")
            }
            if _,_,_,e=bridge.sealNativeNormalObservedLinux([]byte("wrong"),uint32(iface.Index+1));e==nil{
                t.Fatal("wrong kernel interface scope")
            }
            payload:=[]byte("real-local-kernel-interface-budget")
            wire,pn,seq,e:=bridge.sealNativeNormalObservedLinux(payload,uint32(iface.Index))
            if e!=nil||pn!=0||seq!=bridge.txBoundary{t.Fatalf("first TX: %v %d %d",e,pn,seq)}
            got,e:=opener.OpenRecord(wire)
            if e!=nil||got.PN!=pn||got.Kind!=tlsrecord.KindLINK||!bytes.Equal(got.Payload,payload){
                t.Fatalf("Go V4 verification: %+v %v",got,e)
            }
            if _,_,_,e=bridge.sealNativeNormalObservedLinux(bytes.Repeat([]byte{1},1340),uint32(iface.Index));e==nil{
                t.Fatal("SYN peer MSS ignored")
            }
            second:=[]byte("next-pn-and-seq")
            wire2,pn2,seq2,e:=bridge.sealNativeNormalObservedLinux(second,uint32(iface.Index))
            if e!=nil||pn2!=1||seq2!=seq+uint32(len(wire)){
                t.Fatalf("second TX: %v %d %d",e,pn2,seq2)
            }
            got,e=opener.OpenRecord(wire2)
            if e!=nil||!bytes.Equal(got.Payload,second){t.Fatalf("second Go decode: %v",e)}
            if e=bridge.stopAndRelease();e!=nil{t.Fatal(e)}
            if _,_,_,e=bridge.sealNativeNormalObservedLinux([]byte("stale"),uint32(iface.Index));e==nil{
                t.Fatal("old owner still TX after Stop")
            }
            if e=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);e!=nil{t.Fatal(e)}
        })
    }
}

func TestR0V4NativeRustLinuxKernelRoutePmtu(t *testing.T){
    lo,err:=net.InterfaceByName("lo")
    if err!=nil||lo==nil||lo.Index<=0||lo.MTU<576{
        t.Fatalf("Linux lo not available: %v",err)
    }
    loopback:=[4]byte{127,0,0,1}
    for _,suite:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(fmt.Sprintf("suite-%d",suite),func(t *testing.T){
            bridge:=&v4NativeRustProbe{}
            if _,_,_,err:=bridge.sealNativeNormalKernelRoute([]byte("early"),uint32(lo.Index),loopback);err==nil{
                t.Fatal("uncommitted route observation emitted TX")
            }
            store,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,bridge,store,suite)
            if ce!=nil||se!=nil||client==nil||server==nil||!bridge.committed {
                t.Fatalf("real V4 TLS: %v %v",ce,se)
            }
            cold,err:=client.ColdSnapshot();if err!=nil{t.Fatal(err)}
            limit,_:=cold.RecordLimits()
            opener,err:=tlsrecord.NewOpenerForCipher(cold.DirectionKeys().S2C,int(limit),suite)
            if err!=nil{t.Fatal(err)}
            if _,_,_,err=bridge.sealNativeNormalKernelRoute([]byte("bad"),0,loopback);err==nil{
                t.Fatal("missing scope accepted route")
            }
            if _,_,_,err=bridge.sealNativeNormalKernelRoute([]byte("bad"),uint32(lo.Index+1),loopback);err==nil{
                t.Fatal("incorrect route ifindex accepted")
            }
            if _,_,_,err=bridge.sealNativeNormalKernelRoute([]byte("bad"),uint32(lo.Index),[4]byte{});err==nil{
                t.Fatal("unspecified route destination accepted")
            }
            if _,_,_,err=bridge.sealNativeNormalKernelRoute([]byte("bad"),uint32(lo.Index),[4]byte{255,255,255,255});err==nil{
                t.Fatal("broadcast route destination accepted")
            }
            payload:=[]byte("v4-rust-real-kernel-routed-normal-off")
            wire,pn,seq,err:=bridge.sealNativeNormalKernelRoute(payload,uint32(lo.Index),loopback)
            if err!=nil||pn!=0||seq!=bridge.txBoundary {
                t.Fatalf("first scoped route TX: %v pn=%d seq=%d",err,pn,seq)
            }
            got,err:=opener.OpenRecord(wire)
            if err!=nil||got.PN!=pn||got.Kind!=tlsrecord.KindLINK||!bytes.Equal(got.Payload,payload){
                t.Fatalf("actual Go V4 S2C route packet failed: %v",err)
            }
            if _,_,_,err=bridge.sealNativeNormalKernelRoute(bytes.Repeat([]byte{9},1340),uint32(lo.Index),loopback);err==nil{
                t.Fatal("route MTU widened original SYN MSS")
            }
            follow:=[]byte("next-route-scoped-packet")
            wire2,pn2,seq2,err:=bridge.sealNativeNormalKernelRoute(follow,uint32(lo.Index),loopback)
            if err!=nil||pn2!=1||seq2!=seq+uint32(len(wire)){
                t.Fatalf("route TX PN or exact TCP seq reused: %v %d %d",err,pn2,seq2)
            }
            got,err=opener.OpenRecord(wire2)
            if err!=nil||got.PN!=pn2||!bytes.Equal(got.Payload,follow){
                t.Fatalf("actual Go V4 route second packet: %v",err)
            }
            if err=bridge.stopAndRelease();err!=nil{t.Fatal(err)}
            if _,_,_,err=bridge.sealNativeNormalKernelRoute([]byte("after-stop"),uint32(lo.Index),loopback);err==nil{
                t.Fatal("retired owner accepted routed TX")
            }
            if err=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);err!=nil{t.Fatal(err)}
        })
    }
}

// First actual kernel hop of this system's V4 Normal/off ciphertext:
// normal-build Rust AEAD/PN -> original ScopedOwner M1 FrozenRecord ->
// normal-build M4 bounded sendmmsg -> Linux UDP loopback -> Go kernel
// ReadFromUDP -> REAL Go TLS-derived S2C Opener. No fake in-memory wire
// transfer is allowed in the positive branch. UDP is not product TUN/raw.
func TestR0V4NativeRustM4KernelUdpScopedTxFirstPacket(t *testing.T){
    iface,e:=net.InterfaceByName("lo")
    if e!=nil||iface==nil||iface.Index<1{t.Fatalf("Linux loopback: %v",e)}
    loopback:=net.IPv4(127,0,0,1)
    for _,suite:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(fmt.Sprintf("cipher-%d",suite),func(t *testing.T){
            sock,e:=net.ListenUDP("udp4",&net.UDPAddr{IP:loopback,Port:0})
            if e!=nil{t.Fatal(e)}
            defer sock.Close()
            port:=sock.LocalAddr().(*net.UDPAddr).Port
            bridge:=&v4NativeRustProbe{}
            if _,_,_,e=bridge.sendKernelUDP([]byte("before-detach"),uint32(iface.Index),uint16(port));e==nil{
                t.Fatal("M4 accepted V4 before original Go protected admission")
            }
            store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,bridge,store,suite)
            if ce!=nil||se!=nil||client==nil||server==nil||!bridge.committed{
                t.Fatalf("real Go TLS: %v %v",ce,se)
            }
            clientCold,e:=client.ColdSnapshot();if e!=nil{t.Fatal(e)}
            cLimit,_:=clientCold.RecordLimits()
            opener,e:=tlsrecord.NewOpenerForCipher(
                clientCold.DirectionKeys().S2C,int(cLimit),suite,
            )
            if e!=nil{t.Fatal(e)}
            // Wrong kernel ifindex and invalid receiver must not spend PN.
            if _,_,_,e=bridge.sendKernelUDP([]byte("wrong-index"),uint32(iface.Index+1),uint16(port));e==nil{
                t.Fatal("kernel-bound scope bypassed on wrong ifindex")
            }
            if _,_,_,e=bridge.sendKernelUDP([]byte("no-port"),uint32(iface.Index),0);e==nil{
                t.Fatal("driver accepted absent kernel recipient")
            }
            payload:=[]byte("first-real-kernel-normal-off-S2C-business-candidate")
            pn,seq,n,e:=bridge.sendKernelUDP(payload,uint32(iface.Index),uint16(port))
            if e!=nil||pn!=0||seq!=bridge.txBoundary||n<=uint32(len(payload)){
                t.Fatalf("real M4 first submit: %v pn=%d seq=%d size=%d",e,pn,seq,n)
            }
            if e=sock.SetReadDeadline(time.Now().Add(2*time.Second));e!=nil{t.Fatal(e)}
            buf:=make([]byte,2048)
            gotSize,peer,e:=sock.ReadFromUDP(buf)
            if e!=nil||gotSize!=int(n)||peer==nil||!peer.IP.Equal(loopback){
                t.Fatalf("no real kernel UDP record: %v got=%d want=%d sender=%v",e,gotSize,n,peer)
            }
            opened,e:=opener.OpenRecord(buf[:gotSize])
            if e!=nil||opened.PN!=pn||opened.Kind!=tlsrecord.KindLINK||
                !bytes.Equal(opened.Payload,payload){
                t.Fatalf("real UDP ciphertext not Go-TLS-authentic: %+v %v",opened,e)
            }
            // Second separate sendmmsg must be a fresh PN and TCP seq.
            payload2:=[]byte("second-distinct-real-kernel-record")
            pn2,seq2,n2,e:=bridge.sendKernelUDP(payload2,uint32(iface.Index),uint16(port))
            if e!=nil||pn2!=pn+1||seq2!=seq+n {t.Fatalf("second scoped M4: %v pn=%d seq=%d",e,pn2,seq2)}
            gotSize,_,e=sock.ReadFromUDP(buf)
            if e!=nil||gotSize!=int(n2){t.Fatalf("second kernel read: %v",e)}
            opened2,e:=opener.OpenRecord(buf[:gotSize])
            if e!=nil||opened2.PN!=pn2||!bytes.Equal(opened2.Payload,payload2){
                t.Fatalf("second independent TLS auth: %+v %v",opened2,e)
            }
            if e=bridge.stopAndRelease();e!=nil{t.Fatal(e)}
            if _,_,_,e=bridge.sendKernelUDP([]byte("stale"),uint32(iface.Index),uint16(port));e==nil{
                t.Fatal("M4 emitted ciphertext after Stop")
            }
            if e=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);e!=nil{t.Fatal(e)}
        })
    }
}

// Actual Linux C2S RX vertical slice: Go's TLS-derived V4 C2S record is
// transmitted through the kernel UDP stack, M4 recvmmsg writes DIRECTLY
// into an ORIGINAL M1 UniqueBuffer, original ScopedOwner performs AEAD/PN
// + M3 LINK and calls the complete normal business candidate callback.
// This fixture remains UDP, not production AF_PACKET/TUN or app delivery.
func TestR0V4NativeRustM4KernelUdpC2SIntoOriginalOwner(t *testing.T){
    loopback:=net.IPv4(127,0,0,1)
    for _,suite:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(fmt.Sprintf("cipher-%d",suite),func(t *testing.T){
            store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
            bridge:=&v4NativeRustProbe{}
            if _,e=bridge.bindKernelRx();e==nil{
                t.Fatal("kernel M4 RX bound before Go protected session")
            }
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,bridge,store,suite)
            if ce!=nil||se!=nil||client==nil||server==nil||!bridge.committed {
                t.Fatalf("protected Go V4 admission: %v %v",ce,se)
            }
            port,e:=bridge.bindKernelRx();if e!=nil{t.Fatal(e)}
            if _,e=bridge.bindKernelRx();e==nil{t.Fatal("second kernel RX binding")}
            cold,e:=client.ColdSnapshot();if e!=nil{t.Fatal(e)}
            _,maxServer:=cold.RecordLimits()
            sealer,e:=tlsrecord.NewSealerForCipher(
                cold.DirectionKeys().C2S,int(maxServer),suite)
            if e!=nil{t.Fatal(e)}
            sender,e:=net.DialUDP("udp4",nil,&net.UDPAddr{IP:loopback,Port:int(port)})
            if e!=nil{t.Fatal(e)}
            defer sender.Close()
            // No delivery if kernel has not yet received a packet.
            if _,_,e=bridge.receiveKernelRx();e==nil{
                t.Fatal("empty kernel recvmmsg granted a business callback")
            }
            payload:=[]byte("first-authenticated-C2S-normal-off-via-real-Linux-kernel-RX")
            wire,pn,e:=sealer.Seal(payload)
            if e!=nil||pn!=0{t.Fatalf("Go C2S record: %v PN=%d",e,pn)}
            if n,e:=sender.Write(wire);e!=nil||n!=len(wire){
                t.Fatalf("Go kernel UDP send: n=%d e=%v",n,e)
            }
            gotPN,digest,e:=bridge.receiveKernelRx()
            want:=fnv.New64a();_,_=want.Write(payload)
            if e!=nil||gotPN!=pn||digest!=want.Sum64(){
                t.Fatalf("kernel recvmmsg M1 ScopedOwner AEAD/M3 callback: e=%v pn=%d digest=%x expected=%x",e,gotPN,digest,want.Sum64())
            }
            // Genuine kernel replay: another datagram, same valid ciphertext
            // and same PN; no second business candidate is permitted.
            if n,e:=sender.Write(wire);e!=nil||n!=len(wire){t.Fatalf("replay UDP: %v",e)}
            if _,_,e=bridge.receiveKernelRx();e==nil{
                t.Fatal("kernel-received authenticated PN replay redelivered")
            }
            tampered:=append([]byte(nil),wire...)
            tampered[len(tampered)-1]^=0x10
            if n,e:=sender.Write(tampered);e!=nil||n!=len(tampered){t.Fatalf("corrupt UDP: %v",e)}
            if _,_,e=bridge.receiveKernelRx();e==nil{
                t.Fatal("tampered kernel-received AEAD record published")
            }
            if e=bridge.stopAndRelease();e!=nil{t.Fatal(e)}
            nextWire,_,e:=sealer.Seal([]byte("old-owner-after-stop"))
            if e!=nil{t.Fatal(e)}
            // Old UDP destination is now closed; an OS send may or may not
            // report ICMP, but MUST never re-enable the retired Rust owner.
            _,_=sender.Write(nextWire)
            if _,_,e=bridge.receiveKernelRx();e==nil{
                t.Fatal("retired scoped M4 receiver delivered after Stop")
            }
            if e=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);e!=nil{t.Fatal(e)}
        })
    }
}

// Diagnostic-only representative GO HEAP RETAINED metric, NOT process RSS,
// native Rust buffers, physical memory nor a hard per-lane steady-state
// guarantee. Measures authentic Go client+server TLS+FakeTCP pair references
// remaining after Go GC, over 12 real V4 admission pairs at rest. Separately
// retiring Rust owners avoids claiming retained native allocator as Go heap.
func TestR0V4NativeRustGoAdmissionRetainedHeapIndicative(t *testing.T){
    const count=12
    runtime.GC()
    var before runtime.MemStats
    runtime.ReadMemStats(&before)
    type sample struct{
        client *V4ClientSession
        server *V4ServerSession
        bridge *v4NativeRustProbe
        store *V4EpochStore
    }
    samples:=make([]sample,0,count)
    for i:=0;i<count;i++{
        store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
        bridge:=&v4NativeRustProbe{}
        c,s,ce,se:=v4PairWithPrivateBridgeCipher(t,bridge,store,CipherChaCha)
        if ce!=nil||se!=nil||c==nil||s==nil||!bridge.committed{
            t.Fatalf("real Go admission sample %d: %v %v",i,ce,se)
        }
        samples=append(samples,sample{c,s,bridge,store})
    }
    runtime.GC()
    var after runtime.MemStats
    runtime.ReadMemStats(&after)
    // Keep both session objects and their TLS pointers rooted through GC.
    runtime.KeepAlive(samples)
    delta:=int64(after.HeapAlloc)-int64(before.HeapAlloc)
    t.Logf("GO_V4_RETAINED_HEAP indicative_client_plus_server_pair_count=%d delta_bytes=%d per_pair_bytes=%d heap_inuse_delta_bytes=%d go_version=%s",
        count,delta,delta/count,int64(after.HeapInuse)-int64(before.HeapInuse),runtime.Version())
    if delta<=0 {
        t.Fatal("Go V4 GC-after heap sample unexpectedly nonpositive")
    }
    for _,a:=range samples{
        if e:=a.bridge.stopAndRelease();e!=nil{t.Fatal(e)}
        if e:=a.store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,a.server.Epoch);e!=nil{t.Fatal(e)}
    }
    runtime.KeepAlive(samples)
}

// Real Linux namespace TUN app-egress first packet. Run ONLY by the
// privileged owned namespace runner; ordinary CI runs skip this test.
// No mock destination: Go application socket must receive a packet injected
// into the actual /dev/net/tun FD by normal-build Rust after AEAD/M3.
func TestR0V4NativeRustTunKernelAppFirst(t *testing.T){
    if os.Getenv("WBD_REAL_TUN")!="1"{t.Skip("TUN real namespace capability test is opt-in")}
    const name="wbdtunn0"
    f,e:=os.OpenFile("/dev/net/tun",os.O_RDWR,0)
    if e!=nil{t.Fatalf("TUN_UNSUPPORTED open /dev/net/tun: %v",e)}
    defer f.Close()
    var ifreq [40]byte // native Linux x86_64 ifreq
    copy(ifreq[:16],[]byte(name))
    binary.LittleEndian.PutUint16(ifreq[16:18],0x1001) // IFF_TUN|IFF_NO_PI
    _,_,errno:=syscall.Syscall(syscall.SYS_IOCTL,f.Fd(),0x400454ca,
        uintptr(unsafe.Pointer(&ifreq[0]))) // TUNSETIFF
    if errno!=0{t.Fatalf("TUN_UNSUPPORTED ioctl TUNSETIFF: %v",errno)}
    if out,e:=exec.Command("ip","addr","add","10.240.20.1/24","dev",name).CombinedOutput();e!=nil{
        t.Fatalf("TUN configure address: %v %s",e,out)
    }
    if out,e:=exec.Command("ip","link","set","dev",name,"up").CombinedOutput();e!=nil{
        t.Fatalf("TUN configure up: %v %s",e,out)
    }
    dstIP:=net.IPv4(10,240,20,1)
    senderIP:=net.IPv4(10,240,20,2)
    loIP:=net.IPv4(127,0,0,1)
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(fmt.Sprintf("suite-%d",cipher),func(t *testing.T){
            store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
            bridge:=&v4NativeRustProbe{}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,bridge,store,cipher)
            if ce!=nil||se!=nil||client==nil||server==nil||!bridge.committed {
                t.Fatalf("Go real protected V4 TLS: %v %v",ce,se)
            }
            port,e:=bridge.bindKernelRx();if e!=nil{t.Fatal(e)}
            if e=bridge.attachKernelTun(f.Fd(),name);e!=nil{t.Fatal(e)}
            app,e:=net.ListenUDP("udp4",&net.UDPAddr{IP:dstIP,Port:0})
            if e!=nil{t.Fatalf("actual Linux application UDP bind: %v",e)}
            defer app.Close()
            c,e:=client.ColdSnapshot();if e!=nil{t.Fatal(e)}
            clientLimit,limit:=c.RecordLimits()
            sealer,e:=tlsrecord.NewSealerForCipher(c.DirectionKeys().C2S,int(limit),cipher)
            if e!=nil{t.Fatal(e)}
            udp,e:=net.DialUDP("udp4",nil,&net.UDPAddr{IP:loIP,Port:int(port)})
            if e!=nil{t.Fatal(e)}
            defer udp.Close()
            payload:=[]byte("verified-IPV4-app-TUN-business-first")
            packet:=make([]byte,20+8+len(payload))
            packet[0]=0x45;packet[8]=64;packet[9]=17
            binary.BigEndian.PutUint16(packet[2:4],uint16(len(packet)))
            binary.BigEndian.PutUint16(packet[4:6],uint16(17+cipher))
            copy(packet[12:16],senderIP.To4())
            copy(packet[16:20],dstIP.To4())
            var sum uint32
            for i:=0;i<20;i+=2{sum+=uint32(binary.BigEndian.Uint16(packet[i:i+2]))}
            for sum>>16!=0{sum=(sum&0xffff)+(sum>>16)}
            binary.BigEndian.PutUint16(packet[10:12],^uint16(sum))
            binary.BigEndian.PutUint16(packet[20:22],40001)
            binary.BigEndian.PutUint16(packet[22:24],uint16(app.LocalAddr().(*net.UDPAddr).Port))
            binary.BigEndian.PutUint16(packet[24:26],uint16(8+len(payload)))
            // UDP checksum==0 is legal in IPv4, no fake packet contents.
            copy(packet[28:],payload)
            wire,pn,e:=sealer.Seal(packet)
            if e!=nil||pn!=0{t.Fatalf("protected C2S record: %v pn=%d",e,pn)}
            if n,e:=udp.Write(wire);e!=nil||n!=len(wire){t.Fatalf("Go real C2S UDP: %v",e)}
            delivered,failed,e:=bridge.receiveKernelToTun()
            if e!=nil||delivered!=1||failed!=0{
                t.Fatalf("normal Rust AEAD/M3 -> kernel TUN write: e=%v delivered=%d failed=%d",e,delivered,failed)
            }
            if e=app.SetReadDeadline(time.Now().Add(2*time.Second));e!=nil{t.Fatal(e)}
            got:=make([]byte,256)
            n,peer,e:=app.ReadFromUDP(got)
            if e!=nil||peer==nil||!peer.IP.Equal(senderIP)||!bytes.Equal(got[:n],payload){
                t.Fatalf("NO REAL TUN application kernel UDP first: err=%v peer=%v n=%d",e,peer,n)
            }
            t.Logf("TUN_APP_FIRST_PACKET_PASS suite=%d received=%d via=/dev/net/tun, IP kernel socket",cipher,n)
            // REVERSE actual app leg: the kernel emits this UDP datagram
            // into the SAME real TUN FD; normal Rust M4 read() fills an
            // ORIGINAL M1 slab; the original owner seals S2C and M4 uses
            // real sendmmsg into an independent Go kernel UDP socket.
            peerSocket,e:=net.ListenUDP("udp4",&net.UDPAddr{IP:loIP,Port:0})
            if e!=nil{t.Fatal(e)}
            defer peerSocket.Close()
            remote:=&net.UDPAddr{IP:senderIP,Port:42001}
            reverse:=[]byte("reverse-real-app-TUN-to-Rust-AEAD-and-Go-peer")
            if written,e:=app.WriteToUDP(reverse,remote);e!=nil||written!=len(reverse){
                t.Fatalf("Linux UDP app could not originate TUN packet: n=%d err=%v",written,e)
            }
            nif,e:=net.InterfaceByName("lo")
            if e!=nil||nif.Index<1{t.Fatal(e)}
            pn2,seq2,wireLen,appLen,e:=bridge.tunToKernelUDP(
                uint32(nif.Index),uint16(peerSocket.LocalAddr().(*net.UDPAddr).Port))
            if e!=nil||pn2!=0||seq2!=bridge.txBoundary{
                t.Fatalf("Rust TUN source to M4 sendmmsg: %v pn=%d seq=%d",e,pn2,seq2)
            }
            if e=peerSocket.SetReadDeadline(time.Now().Add(2*time.Second));e!=nil{t.Fatal(e)}
            sealed:=make([]byte,2048)
            wireN,peerAddr,e:=peerSocket.ReadFromUDP(sealed)
            if e!=nil||peerAddr==nil||!peerAddr.IP.Equal(loIP)||wireN!=int(wireLen){
                t.Fatalf("Linux Go peer did not receive actual M4 record: %v n=%d wire=%d",e,wireN,wireLen)
            }
            opener,e:=tlsrecord.NewOpenerForCipher(
                c.DirectionKeys().S2C,int(clientLimit),cipher)
            if e!=nil{t.Fatal(e)}
            opened,e:=opener.OpenRecord(sealed[:wireN])
            if e!=nil||opened.Kind!=tlsrecord.KindLINK||opened.PN!=pn2{
                t.Fatalf("Go TLS peer rejected real TUN app S2C: %+v %v",opened,e)
            }
            ip:=opened.Payload
            if len(ip)!=int(appLen)||len(ip)<28+len(reverse) ||
                ip[0]!=0x45||ip[9]!=17||
                !net.IP(ip[12:16]).Equal(dstIP)||
                !net.IP(ip[16:20]).Equal(senderIP)||
                !bytes.Equal(ip[28:],reverse){
                t.Fatalf("real TUN kernel app packet lost: got=%x appLen=%d",ip,appLen)
            }
            t.Logf("TUN_APP_REVERSE_PACKET_PASS suite=%d received=%d via=kernel TUN read + original Rust AEAD + M4 sendmmsg",cipher,len(reverse))
            if e=bridge.stopAndRelease();e!=nil{t.Fatal(e)}
            if _,_,e=bridge.receiveKernelToTun();e==nil{
                t.Fatal("retired normal Rust scoped TUN owner allowed delivery")
            }
            if _,_,_,_,e=bridge.tunToKernelUDP(uint32(nif.Index),uint16(peerSocket.LocalAddr().(*net.UDPAddr).Port));e==nil{
                t.Fatal("retired Rust scoped owner permitted reverse TUN->AEAD TX")
            }
            if e=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);e!=nil{t.Fatal(e)}
        })
    }
}
