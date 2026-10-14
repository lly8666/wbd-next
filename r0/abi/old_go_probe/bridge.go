// Package r0bridge contains a real cgo boundary compiled in the fixed old
// Go module, calling Rust's native C ABI via wbd_abi.h. NOT production wiring.
package r0bridge

/*
#include "wbd_abi.h"
*/
import "C"
import "unsafe"

const (
    OK = int(C.WBD_R0_OK)
    NullArg = int(C.WBD_R0_NULL_ARG)
    BadSize = int(C.WBD_R0_BAD_SIZE)
    BadVersion = int(C.WBD_R0_BAD_VERSION)
    Unsupported = int(C.WBD_R0_UNSUPPORTED)
    Stale = int(C.WBD_R0_STALE)
    NoCapacity = int(C.WBD_R0_NO_CAPACITY)
)
type Info struct { Version uint32; Size uint32; Features uint64 }
type Engine uint64
type Lane uint64

func Query(size uint32)(Info,int){
    result:=C.WbdAbiInfoV1{}
    rc:=int(C.wbd_r0_abi_query(&result,C.uint32_t(size)))
    return Info{uint32(result.abi_version),uint32(result.struct_size),uint64(result.features)},rc
}
func Open(version,size,flags,reserved uint32)(Engine,int){
    cfg:=C.WbdAbiConfigV1{abi_version:C.uint32_t(version),
        struct_size:C.uint32_t(size),flags:C.uint32_t(flags),reserved:C.uint32_t(reserved)}
    out:=C.WbdEngineToken{value:0x55}
    rc:=int(C.wbd_r0_engine_open(&cfg,C.uint32_t(size),&out))
    return Engine(uint64(out.value)),rc
}
func OpenNilConfig()int{
    out:=C.WbdEngineToken{}
    return int(C.wbd_r0_engine_open(nil,16,&out))
}
func OpenNilOutput()int{
    cfg:=C.WbdAbiConfigV1{abi_version:1,struct_size:16}
    return int(C.wbd_r0_engine_open(&cfg,16,nil))
}
func Spawn(engine Engine)(Lane,int){
    out:=C.WbdLaneToken{}
    rc:=int(C.wbd_r0_lane_open(C.WbdEngineToken{value:C.uint64_t(engine)},&out))
    return Lane(uint64(out.value)),rc
}
func SpawnNil(engine Engine)int{
    return int(C.wbd_r0_lane_open(C.WbdEngineToken{value:C.uint64_t(engine)},nil))
}
func CloseEngine(engine Engine)int{
    return int(C.wbd_r0_engine_close(C.WbdEngineToken{value:C.uint64_t(engine)}))
}
func CloseLane(lane Lane)int{
    return int(C.wbd_r0_lane_close(C.WbdLaneToken{value:C.uint64_t(lane)}))
}
func CWidths()(uintptr,uintptr,uintptr,uintptr) {
    return unsafe.Sizeof(C.WbdAbiInfoV1{}),unsafe.Sizeof(C.WbdAbiConfigV1{}),
        unsafe.Sizeof(C.WbdEngineToken{}),unsafe.Sizeof(C.WbdLaneToken{})
}
