//go:build windows && wbd_v4_embedded_go
package realityfront

import (
 "context"
 "errors"
 "runtime"
 "unsafe"
)

// Source-authoritative Rust M2 effective limits. These are actual live
// owner values, not requested CLI switches and not proof of throughput.
type V4WindowsM2Effective struct{
 Version uint32 `json:"version"`
 Size uint32 `json:"size"`
 PathMTU uint32 `json:"path_mtu"`
 BusinessIPv4MTU uint32 `json:"business_ipv4_mtu"`
 RepairShadowLimit uint32 `json:"optional_repair_shadow_limit"`
 FeedbackPageLimit uint32 `json:"feedback_retained_pages"`
 MatureLiveLimit uint32 `json:"auto_mature_metadata_limit"`
 V3Enabled uint32 `json:"opportunistic_v3_enabled"`
 ProcessRepairHardCap uint64 `json:"process_repair_cap_bytes_per_second"`
 DirectionEpochLimit uint64 `json:"direction_effective_epoch_repair_limit_bytes"`
 DirectionFreshConfirmed uint64 `json:"direction_accepted_fresh_bytes"`
 ProcessChargedRepairs uint64 `json:"process_charged_repair_bytes"`
 ProcessPendingBytes uint64 `json:"process_pending_repair_bytes"`
}
func(s *V4WindowsAuthenticatedClientOwner) ReadBoundOriginalM2Effective(
 ctx context.Context,
)(V4WindowsM2Effective,error){
 var out V4WindowsM2Effective
 if s==nil||s.bridge==nil||s.device==nil||ctx==nil{return out,errV4WindowsOwner}
 loan,err:=s.device.borrowHot(ctx)
 if err!=nil{return out,errors.Join(errV4WindowsOwner,err)}
 defer loan()
 proc,err:=s.bridge.fixedProc("wbd_m0_win_owner_v9_m2_effective")
 if err!=nil{return out,errors.Join(errV4WindowsOwner,err)}
 err=winOwnerCall(proc,uintptr(s.bridge.handle),
  uintptr(unsafe.Pointer(&s.bridge.epoch[0])),16,
  uintptr(s.device.identity.LUID),uintptr(s.device.identity.InterfaceIndex),
  uintptr(unsafe.Pointer(&out)),uintptr(unsafe.Sizeof(out)))
 runtime.KeepAlive(s.bridge.epoch)
 if err!=nil||out.Version!=1||out.Size!=uint32(unsafe.Sizeof(out))||
  out.PathMTU<576||out.BusinessIPv4MTU<20||
  out.BusinessIPv4MTU>out.PathMTU||out.RepairShadowLimit==0||
  out.FeedbackPageLimit==0||out.V3Enabled!=1||
  out.ProcessRepairHardCap==0{
  return V4WindowsM2Effective{},errors.Join(errV4WindowsOwner,err)
 }
 return out,nil
}
