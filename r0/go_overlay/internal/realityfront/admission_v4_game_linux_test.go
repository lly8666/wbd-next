//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product

package realityfront

import "testing"

// Linux-only original Game4 native bridge test. Source protected TLS
// helpers stay in admission_v4_test.go for all platforms; Windows
// should not need the Linux-only native Game lane type to compile.
// A server-returned Epoch cannot distinguish two ORIGINAL protected client
// intents: a cold ZERO-epoch full Game4 group and an explicit old-epoch
// single-lane successor. Real TLS/M1 admission must freeze the REQUEST
// before the server replies with the shared logical epoch.
func TestPLAN028Game4ProtectedEpochZeroWholeGroupVsSingleLane(t *testing.T){
    store,e:=NewV4EpochStore(4)
    if e!=nil{t.Fatal(e)}
    policy,e:=FixedPolicyForClient(4,0)
    if e!=nil{t.Fatal(e)}
    tunnel:=make([]byte,16);tunnel[0]=113
    var zero [16]byte
    _,first,clientErr,serverErr:=v4PairFeatureProbe(t,store,
        "game4",tunnel,1,policy,zero,true,true,true,false,true)
    if clientErr!=nil||serverErr!=nil||first==nil{
        t.Fatalf("original protected fresh group TLS client=%v server=%v",clientErr,serverErr)
    }
    firstLane:=&V4LinuxGameAuthenticatedLane{
        session:first,bridge:&v4EmbeddedNativeBridge{},
    }
    fresh,e:=firstLane.ProtectedFreshGroupRequested()
    if e!=nil||!fresh{t.Fatalf("zero epoch request must stage complete Game4 group: %v %v",fresh,e)}
    _,next,clientErr,serverErr:=v4PairFeatureProbe(t,store,
        "game4",tunnel,1,policy,first.Epoch,true,true,true,false,true)
    if clientErr!=nil||serverErr!=nil||next==nil{
        t.Fatalf("original protected single lane reauth TLS client=%v server=%v",clientErr,serverErr)
    }
    hotLane:=&V4LinuxGameAuthenticatedLane{
        session:next,bridge:&v4EmbeddedNativeBridge{},
    }
    hot,e:=hotLane.ProtectedFreshGroupRequested()
    if e!=nil||hot{t.Fatalf("explicit old epoch must be single-lane hot: %v %v",hot,e)}
    if next.Epoch!=first.Epoch{
        t.Fatal("server-shared epoch changed; this is not the intended ambiguity")
    }
    fake:=&V4LinuxGameAuthenticatedLane{
        session:&V4ServerSession{verifiedRequestedFreshEpoch:true},
        bridge:&v4EmbeddedNativeBridge{},
    }
    if _,e=fake.ProtectedFreshGroupRequested();e==nil{
        t.Fatal("unverified protection must not mint a fresh-group authority")
    }
    for _,s:=range []*V4ServerSession{first,next}{
        snap,e:=s.ColdSnapshot()
        if e!=nil{t.Fatal(e)}
        if e=store.ReleaseLaneInstance("game4",tunnel,1,s.Epoch,snap.Incarnation());e!=nil{
            t.Fatal(e)
        }
    }
}
