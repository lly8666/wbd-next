//go:build linux && cgo && wbd_v4_native_probe

package realityfront
import ("errors";"testing";"hash/fnv";"fmt";"bytes";"encoding/binary";"github.com/lly8666/wobuzhidao/internal/tlsrecord")

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
    if _,e:=b.prepare(V4ColdSessionSnapshot{},0);e==nil{
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
