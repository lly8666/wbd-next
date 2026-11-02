//go:build windows && wbd_v4_embedded_go
package main

import (
 "errors"
 "fmt"
 "path/filepath"
 "runtime"
 "syscall"
 "unsafe"
)

// Exactly matches Rust #[repr(C)] 36-byte v1 input, followed by one
// receive-inner field. Only complete outer IPv4 IP MTU is operator-settable.
type m0RustColdBudgetInput struct {
 Version,Size,OuterIPMTU,PhysicalIPMTU,PeerRawMSS,RecordCap,IPHeader,TCPHeader,Mode uint32
}
type m0RustColdReceiveInput struct{
 Cold m0RustColdBudgetInput
 PlannedReceivingInnerMTU uint32
}
type m0RustColdBudgetOutput struct{
 Version,Size,EffectiveOuterIPMTU,AdvertisedSynMSS,RecordWire,
 RecordPayload,InnerIPCap,LinkFragmentCap uint32
}
// Only an enum-to-Rust-ABI mapping, not a second MTU byte formula.
func m0WindowsV4BudgetMode(mode m0WindowsV4Mode,gameFEC bool)(uint32,error){
 switch mode{
 case m0WinModeNormal:
  if !gameFEC{return 0,nil}
 case m0WinModeFixed,m0WinModeAuto:
  if !gameFEC{return 1,nil}
 case m0WinModeGame2,m0WinModeGame4:
  if gameFEC{return 3,nil}
  return 2,nil
 }
 return 0,fmt.Errorf("Windows V4 cold MTU mode/GameFEC invalid")
}
func m0WindowsV4ColdRecordOffer(library string,outer,physical,plannedInner uint32,
 mode m0WindowsV4Mode,gameFEC bool)(uint16,error){
 if !filepath.IsAbs(library)||filepath.Ext(library)!=".dll"||
  outer<576||outer>1500||plannedInner<576||plannedInner>1500{
  return 0,fmt.Errorf("Windows V4 cold MTU outer/inner/dll invalid")
 }
 kind,err:=m0WindowsV4BudgetMode(mode,gameFEC)
 if err!=nil{return 0,err}
 dll,err:=syscall.LoadDLL(library)
 if err!=nil{return 0,err}
 defer dll.Release()
 proc,err:=dll.FindProc("wbd_m0_v4_mtu_budget_receive_v1")
 if err!=nil{return 0,err}
 in:=m0RustColdReceiveInput{Cold:m0RustColdBudgetInput{
  Version:1,Size:uint32(unsafe.Sizeof(m0RustColdBudgetInput{})),
  OuterIPMTU:outer,
  // Unknown physical egress is zero, not the inner TUN. Linux + Rust
  // active TX route snapshots independently narrow actual local PMTU.
  PhysicalIPMTU:physical,
  PeerRawMSS:outer-40,IPHeader:20,TCPHeader:20,Mode:kind,
 },PlannedReceivingInnerMTU:plannedInner}
 var out m0RustColdBudgetOutput
 rc,_,callErr:=proc.Call(uintptr(unsafe.Pointer(&in)),
  uintptr(unsafe.Sizeof(in)),uintptr(unsafe.Pointer(&out)),
  uintptr(unsafe.Sizeof(out)))
 runtime.KeepAlive(in)
 runtime.KeepAlive(out)
 if rc!=0||out.Version!=1||
  out.Size!=uint32(unsafe.Sizeof(out))||
  out.RecordWire<51||out.RecordWire>1460||
  out.InnerIPCap>plannedInner||out.EffectiveOuterIPMTU>outer{
  return 0,errors.Join(fmt.Errorf("Windows V4 Rust cold MTU ABI refused rc=%d offer=%d",rc,out.RecordWire),callErr)
 }
 return uint16(out.RecordWire),nil
}

// Rust's one pre-TLS budget computes the local source's SYN MSS
// from REAL OS egress IP MTU, not from Wintun's derived inner MTU.
func m0WindowsV4LocalSYNBudget(library string,outer,physical uint32,
 mode m0WindowsV4Mode,gameFEC bool)(m0RustColdBudgetOutput,error){
 if outer<576||outer>1500||physical<576||
  !filepath.IsAbs(library)||filepath.Ext(library)!=".dll"{
  return m0RustColdBudgetOutput{},fmt.Errorf("Rust Windows MSS local physical source invalid")
 }
 kind,err:=m0WindowsV4BudgetMode(mode,gameFEC)
 if err!=nil{return m0RustColdBudgetOutput{},err}
 dll,err:=syscall.LoadDLL(library)
 if err!=nil{return m0RustColdBudgetOutput{},err}
 defer dll.Release()
 proc,err:=dll.FindProc("wbd_m0_v4_mtu_budget_v1")
 if err!=nil{return m0RustColdBudgetOutput{},err}
 input:=m0RustColdBudgetInput{Version:1,Size:uint32(unsafe.Sizeof(m0RustColdBudgetInput{})),
  OuterIPMTU:outer,PhysicalIPMTU:physical,PeerRawMSS:outer-40,
  IPHeader:20,TCPHeader:20,Mode:kind}
 var result m0RustColdBudgetOutput
 rc,_,callErr:=proc.Call(uintptr(unsafe.Pointer(&input)),uintptr(unsafe.Sizeof(input)),
  uintptr(unsafe.Pointer(&result)),uintptr(unsafe.Sizeof(result)))
 runtime.KeepAlive(input);runtime.KeepAlive(result)
 if rc!=0||result.Version!=1||result.Size!=uint32(unsafe.Sizeof(result))||
  result.EffectiveOuterIPMTU>outer||result.EffectiveOuterIPMTU>physical||
  result.AdvertisedSynMSS<536||result.AdvertisedSynMSS>1460||result.InnerIPCap<576{
  return m0RustColdBudgetOutput{},errors.Join(fmt.Errorf(
   "Rust original Windows SYN MSS refused rc=%d mss=%d effective_outer=%d",
   rc,result.AdvertisedSynMSS,result.EffectiveOuterIPMTU),callErr)
 }
 return result,nil
}
