//go:build linux && cgo && wbd_v4_native_probe

package realityfront
import ("errors";"testing")

// Actual Go protected TLS reaches Rust's independent fresh ScopedOwner using
// the package-private Prepare/Detach/Commit hook; production still disabled.
func TestR0V4NativeRustProbeActualProtectedFreshOwner(t *testing.T){
    store,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
    var first uint64
    for i:=0;i<2;i++{
        b:=&v4NativeRustProbe{}
        c,s,ce,se:=v4PairWithPrivateBridge(t,b,store)
        if ce!=nil||se!=nil||c==nil||s==nil{
            t.Fatalf("real protected TLS %d: client=%v server=%v",i,ce,se)
        }
        if !b.prepared||!b.committed||b.handle==0{t.Fatal("no fresh Rust candidate")}
        if phase,e:=b.state();e!=nil||phase!=2{
            t.Fatalf("Rust owner not committed after Go detach: phase=%d err=%v",phase,e)
        }
        if i==1 && b.handle==first{t.Fatal("Rust generation reused")}
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
