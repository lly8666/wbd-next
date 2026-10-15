//go:build linux && cgo && wbd_v4_native_probe

package realityfront
import ("errors";"testing";"hash/fnv")

// Actual Go protected TLS reaches Rust's independent fresh ScopedOwner using
// the package-private Prepare/Detach/Commit hook; production still disabled.
func TestR0V4NativeRustProbeActualProtectedFreshOwner(t *testing.T){
    store,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
    var first uint64
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
        count,size,digest,e:=b.drainEarly()
        if e!=nil{t.Fatal(e)}
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
        if e:=b.stopAndRelease();e!=nil{t.Fatal(e)}
        if _,e:=b.state();!errors.Is(e,errV4NativeProbe){
            t.Fatal("released Rust generation still addressable")
        }
        if e:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,s.Epoch);e!=nil{
            t.Fatal(e)
        }
    }
    b:=&v4NativeRustProbe{}
    if _,e:=b.prepare(V4ColdSessionSnapshot{},0);e==nil{
        t.Fatal("forged empty snapshot minted Rust owner candidate")
    }
}
