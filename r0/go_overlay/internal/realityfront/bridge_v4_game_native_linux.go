//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product

package realityfront

/*
#include <stdint.h>
#include <stddef.h>
extern int32_t wbd_m0_embedded_go_game_group_join(const uint64_t *,size_t,uint32_t,uint64_t *);
extern int32_t wbd_m0_embedded_go_game_group_state(uint64_t,uint32_t *,uint32_t *);
extern int32_t wbd_m0_embedded_go_game_group_stop(uint64_t);
extern int32_t wbd_m0_embedded_go_game_group_release(uint64_t);
*/
import "C"
import (
    "errors"
    "fmt"
    "unsafe"
)

// Non-public binding from a complete verified original-Go TLS 2/4 group
// into one single Rust GameAdapter with per-lane independent AEAD/PN owner.
// A positive return does NOT attest that raw/TUN drivers were installed.
type v4NativeGameJoined struct {
    handle uint64
    laneOwners []*v4EmbeddedNativeBridge
    verified *V4LinuxGameVerifiedGroup
    stopped bool
}
func (g *V4LinuxGameVerifiedGroup) joinAuthenticatedOriginalRust(
    owners ...*v4EmbeddedNativeBridge,
)(*v4NativeGameJoined,error){
    if g==nil||(len(owners)!=2&&len(owners)!=4){return nil,ErrAdmissionParams}
    var result *v4NativeGameJoined
    err:=g.withPrivateOriginalTLS(func(cold []V4ColdSessionSnapshot)error{
        if len(cold)!=len(owners){return ErrAdmissionParams}
        ids:=make([]C.uint64_t,len(cold))
        ordered:=make([]*v4EmbeddedNativeBridge,len(cold))
        for _,o:=range owners{
            if o==nil||o.handle==0||o.stopped||!o.committed||
               o.protectedLane==0||int(o.protectedLane)>len(cold){
                return ErrAdmissionUnsupported
            }
            index:=int(o.protectedLane)-1
            if ordered[index]!=nil{return ErrAdmissionParams}
            orig:=cold[index]
            if o.protectedEpoch!=orig.epoch||o.protectedFeatures!=orig.features||
               o.authenticatedPrincipal!=orig.principal||
               o.serverSide!=orig.server {
                return ErrAdmissionParams
            }
            phase,e:=o.state()
            if e!=nil||phase!=2{return ErrAdmissionUnsupported}
            ordered[index]=o
            ids[index]=C.uint64_t(o.handle)
        }
        var group C.uint64_t
        side:=C.uint32_t(0)
        if cold[0].server {side=1}
        rc:=C.wbd_m0_embedded_go_game_group_join(
            (*C.uint64_t)(unsafe.Pointer(&ids[0])),C.size_t(len(ids)),side,&group,
        )
        if rc!=0||group==0{
            return fmt.Errorf("%w: genuine Go TLS Rust Game group join=%d",errV4Embedded,int(rc))
        }
        result=&v4NativeGameJoined{
            handle:uint64(group),laneOwners:ordered,verified:g,
        }
        return nil
    })
    if err!=nil{return nil,err}
    return result,nil
}
// This is intentionally a two-value state: native Game crypto installed
// is not equivalent to verified M4 drivers or kernel first packet.
func (g *v4NativeGameJoined) originalCryptoState()(lanes uint32,drivers bool,err error){
    if g==nil||g.handle==0||g.stopped{return 0,false,ErrAdmissionUnsupported}
    var n,ready C.uint32_t
    rc:=C.wbd_m0_embedded_go_game_group_state(C.uint64_t(g.handle),&n,&ready)
    if rc!=0{return 0,false,fmt.Errorf("%w: native Game state=%d",errV4Embedded,int(rc))}
    return uint32(n),ready!=0,nil
}
// A joined crypto-only group must Stop BEFORE per-lane original Go owner
// release. Callers must separately prove original M4 drivers and then
// clean owned Go kernel state; this method itself NEVER claims product ON.
func (g *v4NativeGameJoined) stopOriginalOwners()error{
    if g==nil||g.handle==0{return ErrAdmissionUnsupported}
    if g.stopped{return nil}
    rc:=C.wbd_m0_embedded_go_game_group_stop(C.uint64_t(g.handle))
    if rc!=0{return fmt.Errorf("%w: Game group Stop=%d",errV4Embedded,int(rc))}
    var all error
    for _,o:=range g.laneOwners{
        _,err:=o.StopAndReleaseOriginalOwner()
        if err!=nil{all=errors.Join(all,err)}
    }
    if all!=nil{return all}
    rc=C.wbd_m0_embedded_go_game_group_release(C.uint64_t(g.handle))
    if rc!=0{return fmt.Errorf("%w: Game group Release=%d",errV4Embedded,int(rc))}
    if err:=g.verified.revoke();err!=nil{return err}
    g.stopped=true
    return nil
}
