//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product

package v4productcli

import (
    "testing"

    "github.com/lly8666/wobuzhidao/internal/faketcp"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

func gameColdTestFlow(port uint16) faketcp.ServerFlow {
    return faketcp.ServerFlow{
        ClientIP:[4]byte{10,25,0,4},ClientPort:port,
        ServerIP:[4]byte{10,25,0,1},ServerPort:443,
    }
}

// Original H1540 Linux 30%-loss log: stale Game2 lane1 port49336
// survived from a failed cold candidate, then new gen8 lane1 57255
// and lane2 57256 arrived under the SAME protected account+epoch.
// The server may only join the consecutive-port pair from gen8;
// it must never claim 49336+57256 as one native Rust M4 group.
func TestPLAN028Game2ColdRetryCannotMixStaleProtectedEpochLanes(t *testing.T){
    key:=realityfront.V4LinuxGameCohortID{
        Principal:"account-carol-test",TunnelID:[16]byte{1},
        Epoch:[16]byte{2},Lanes:2,
    }
    stale,e:=originalGameColdFlowIdentity(key,1,gameColdTestFlow(49336))
    if e!=nil{t.Fatal(e)}
    fresh1,e:=originalGameColdFlowIdentity(key,1,gameColdTestFlow(57255))
    if e!=nil{t.Fatal(e)}
    fresh2,e:=originalGameColdFlowIdentity(key,2,gameColdTestFlow(57256))
    if e!=nil{t.Fatal(e)}
    if stale==fresh1||stale==fresh2 {t.Fatal("stale Game2 lane joined fresh authenticated cold successor")}
    if fresh1!=fresh2{t.Fatal("same-generation adjacent genuine source ports cannot join")}
    pending:=map[originalGameColdFlowKey]map[uint8]bool{
        stale:{1:true},fresh1:{1:true,2:true},
    }
    if len(pending)!=2||len(pending[stale])!=1||len(pending[fresh1])!=2 {
        t.Fatal("pending cohorts were incorrectly merged before actual M4 owner")
    }
}

func TestPLAN028OriginalGame4ColdPortCohortAndForeignScope(t *testing.T){
    key:=realityfront.V4LinuxGameCohortID{
        Principal:"account-dave-test",TunnelID:[16]byte{9},
        Epoch:[16]byte{4},Lanes:4,
    }
    var group originalGameColdFlowKey
    for lane:=1;lane<=4;lane++{
        k,err:=originalGameColdFlowIdentity(key,uint8(lane),gameColdTestFlow(uint16(44030+lane)))
        if err!=nil{t.Fatal(err)}
        if lane==1{group=k}else if k!=group{t.Fatalf("same protected four-lane group split at lane%d",lane)}
    }
    foreign:=gameColdTestFlow(44032)
    foreign.ClientIP=[4]byte{10,25,0,99}
    k,err:=originalGameColdFlowIdentity(key,2,foreign)
    if err!=nil||k==group{t.Fatal("foreign source address was admitted into Game4 group")}
    foreign=gameColdTestFlow(44032)
    foreign.ServerPort=444
    k,err=originalGameColdFlowIdentity(key,2,foreign)
    if err!=nil||k==group{t.Fatal("different server TCP destination was admitted into group")}
    // Port 65535 is legitimate for the LAST lane when the base and
    // all preceding lanes remain within 1..65535. The OUT-OF-RANGE
    // case must instead use 65535 for lane2 of a four-lane group.
    edge,e:=originalGameColdFlowIdentity(key,4,gameColdTestFlow(65535))
    if e!=nil||edge.firstClientPort!=65532 {
        t.Fatalf("valid last original Game4 lane port=65535 incorrectly rejected: %+v %v",edge,e)
    }
    for _,tc:=range []struct{lanes,id uint8;port uint16}{
        {2,0,41000},{2,3,41000},{4,2,1},{4,2,65535},{3,1,44000},
    }{
        different:=key;different.Lanes=tc.lanes
        if _,err:=originalGameColdFlowIdentity(different,tc.id,gameColdTestFlow(tc.port));err==nil{
            t.Fatalf("invalid cold port scope allowed: %+v",tc)
        }
    }
}
