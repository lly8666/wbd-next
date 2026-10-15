//go:build linux && cgo && wbd_v4_native_probe

package realityfront
import ("errors";"testing";"hash/fnv";"fmt";"github.com/lly8666/wobuzhidao/internal/tlsrecord")

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
