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

// All selector requests must be verified against the real versioned native
// Rust owner, before any Npcap device or host-wide network state is touched.
type m0WindowsV4NativeCapability struct{
 Version,Size,SupportedModes,AuthenticatedLanes,Reserved uint32
}
func m0CheckWindowsV4NativeMode(mode m0WindowsV4Mode,library string)error{
 modes:=map[m0WindowsV4Mode]uint32{
  m0WinModeNormal:1,m0WinModeFixed:2,m0WinModeAuto:4,
  m0WinModeGame2:8,m0WinModeGame4:16,
 }
 bit,ok:=modes[mode]
 if !ok{return fmt.Errorf("unknown native V4 mode %q",mode)}
 if !filepath.IsAbs(library)||filepath.Ext(library)!=".dll"{
  return errors.New("native Rust library path must be absolute and a DLL")
 }
 dll,err:=syscall.LoadDLL(library)
 if err!=nil{return fmt.Errorf("load original native Rust owner: %w",err)}
 defer dll.Release()
 proc,err:=dll.FindProc("wbd_m0_win_owner_v4_mode_capabilities")
 if err!=nil{return fmt.Errorf("original Rust mode ABI missing: %w",err)}
 size:=uint32(unsafe.Sizeof(m0WindowsV4NativeCapability{}))
 cap:=m0WindowsV4NativeCapability{Version:4,Size:size}
 rc,_,_:=proc.Call(uintptr(unsafe.Pointer(&cap)),uintptr(size))
 runtime.KeepAlive(&cap)
 if rc!=0||cap.Version!=4||cap.Size!=size||cap.Reserved!=0{
  return errors.New("native Rust mode capability ABI mismatch")
 }
 if cap.SupportedModes&bit==0{
  return fmt.Errorf("Windows V4 %s original Rust data plane is not implemented (ABI mask %d), cannot downgrade",mode,cap.SupportedModes)
 }
 if (mode==m0WinModeGame2&&cap.AuthenticatedLanes<2)||
    (mode==m0WinModeGame4&&cap.AuthenticatedLanes<4){
  return errors.New("requested Windows V4 Game authenticated lane group is not implemented")
 }
 return nil
}
