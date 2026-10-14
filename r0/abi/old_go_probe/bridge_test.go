package r0bridge

import "testing"

func TestR0AbiNativeWidthsVersionNoFeatures(t *testing.T){
    a,b,c,d:=CWidths()
    if a!=24||b!=16||c!=8||d!=8 {t.Fatalf("cgo struct sizes %d %d %d %d",a,b,c,d)}
    if _,rc:=Query(23);rc!=BadSize {t.Fatalf("old size query %d",rc)}
    i,rc:=Query(24)
    if rc!=OK||i.Version!=1||i.Size!=24||i.Features!=0 {
        t.Fatalf("native ABI handshake %+v code %d",i,rc)
    }
}
func TestR0AbiRejectOldSizeAndUnsupportedV4Feature(t *testing.T){
    for _,size:=range []uint32{0,12,15,17,24} {
        token,rc:=Open(1,size,0,0)
        if rc!=BadSize || token!=Engine(0x55) {t.Fatalf("size=%d token=%x code=%d",size,token,rc)}
    }
    token,rc:=Open(2,16,0,0)
    if rc!=BadVersion||token!=Engine(0x55){t.Fatalf("ABI version accepted: %d %x",rc,token)}
    for _,p:=range [][2]uint32{{1,0},{0,1}} {
        token,rc:=Open(1,16,p[0],p[1])
        if rc!=Unsupported||token!=Engine(0x55){t.Fatalf("unsupported flags accepted: %d %x",rc,token)}
    }
    if rc:=OpenNilConfig();rc!=NullArg {t.Fatalf("nil config code=%d",rc)}
    if rc:=OpenNilOutput();rc!=NullArg {t.Fatalf("nil out code=%d",rc)}
}
func TestR0AbiGoToRustOpaqueLifeAndNoAlias(t *testing.T){
    e,rc:=Open(1,16,0,0)
    if rc!=OK||e==0 {t.Fatalf("open engine %d %x",rc,e)}
    if rc:=SpawnNil(e);rc!=NullArg{t.Fatalf("nil lane output code=%d",rc)}
    lane,rc:=Spawn(e)
    if rc!=OK||lane==0 {t.Fatalf("lane open code=%d",rc)}
    if rc:=CloseLane(Lane(e));rc!=Stale{t.Fatalf("engine kind accepted as lane: %d",rc)}
    if rc:=CloseEngine(Engine(lane));rc!=Stale{t.Fatalf("lane kind accepted as engine: %d",rc)}
    if rc:=CloseLane(lane);rc!=OK{t.Fatalf("close lane %d",rc)}
    if rc:=CloseLane(lane);rc!=Stale{t.Fatalf("duplicate close lane %d",rc)}
    successor,rc:=Spawn(e)
    if rc!=OK||successor==lane{t.Fatalf("recycled slot alias %d %x",rc,successor)}
    if rc:=CloseEngine(e);rc!=OK{t.Fatalf("close engine %d",rc)}
    if rc:=CloseLane(successor);rc!=Stale{t.Fatalf("parent teardown left live lane: %d",rc)}
    if _,rc:=Spawn(e);rc!=Stale {t.Fatalf("closed parent admitted lane: %d",rc)}
    if rc:=CloseEngine(e);rc!=Stale {t.Fatalf("duplicate close engine: %d",rc)}
    newer,rc:=Open(1,16,0,0)
    if rc!=OK||newer==e{t.Fatalf("recycled engine alias %d",rc)}
    if rc:=CloseEngine(newer);rc!=OK{t.Fatalf("close new engine %d",rc)}
}
func TestR0AbiGoToRustCapacityNoClaimOfRealEngine(t *testing.T){
    var engines []Engine
    for i:=0;i<4;i++ {
        e,rc:=Open(1,16,0,0)
        if rc!=OK{t.Fatalf("engine %d rc=%d",i,rc)}
        engines=append(engines,e)
    }
    if _,rc:=Open(1,16,0,0);rc!=NoCapacity{t.Fatalf("engine cap rc=%d",rc)}
    var lanes []Lane
    for i:=0;i<16;i++ {
        lane,rc:=Spawn(engines[0])
        if rc!=OK{t.Fatalf("lane %d rc=%d",i,rc)}
        lanes=append(lanes,lane)
    }
    if _,rc:=Spawn(engines[0]);rc!=NoCapacity {t.Fatalf("lane cap rc=%d",rc)}
    for _,e:=range engines {if rc:=CloseEngine(e);rc!=OK{t.Fatalf("engine close %d",rc)}}
    for _,lane:=range lanes {if rc:=CloseLane(lane);rc!=Stale{t.Fatalf("released lane left alive %d",rc)}}
}
