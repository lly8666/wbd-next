//go:build windows && wbd_v4_embedded_go
package main

import(
 "errors"
 "net/netip"
 "path/filepath"
 "testing"
 "golang.org/x/sys/windows"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
)
func TestPLAN028H1381RealWindowsTwoOriginalNativeDeviceSlots(t *testing.T){
 t.Setenv("GITHUB_ACTIONS","true")
 t.Setenv("WBD_PLAN028_TWO_REAL_CLIENTS","1")
 mk:=func(alias,user,ip string)m0NativeV4Options{
  return m0NativeV4Options{AdapterAlias:alias,Username:user,Lease4:netip.MustParsePrefix(ip),StatePath:filepath.Join(t.TempDir(),alias+"-owned.json")}
 }
 a:=mk("WBDWLCLIENTA","alice","10.66.0.2/32")
 b:=mk("WBDWLCLIENTB","bob","10.66.0.3/32")
 first,e:=m0Plan028WindowsNativeClientSlot(a)
 if e!=nil{t.Fatal("genuine Windows OS event A",e)}
 defer windows.CloseHandle(first)
 second,e:=m0Plan028WindowsNativeClientSlot(b)
 if e!=nil{t.Fatal("genuine Windows OS event B",e)}
 defer windows.CloseHandle(second)
 if dup,err:=m0Plan028WindowsNativeClientSlot(a);err==nil{
  if dup!=0{_ = windows.CloseHandle(dup)}
  t.Fatal("duplicate original device A not fenced")
 }else if dup!=0{t.Fatal("duplicate owner leaked Windows event handle")}
 bad:=mk("WBDWLCLIENTA","bob","10.66.0.3/32")
 if h,err:=m0Plan028WindowsNativeClientSlot(bad);!errors.Is(err,windowsclient.ErrN4NativeGuard){if h!=0{_ = windows.CloseHandle(h)};t.Fatalf("cross-account alias admitted %v",err)}
 bad=mk("WBDWLCLIENTC","carol","10.66.0.4/32")
 if h,err:=m0Plan028WindowsNativeClientSlot(bad);!errors.Is(err,windowsclient.ErrN4NativeGuard){if h!=0{_ = windows.CloseHandle(h)};t.Fatalf("foreign alias admitted %v",err)}
 a.StatePath=filepath.Join(t.TempDir(),"wrong-owned.json")
 if h,err:=m0Plan028WindowsNativeClientSlot(a);!errors.Is(err,windowsclient.ErrN4NativeGuard){if h!=0{_ = windows.CloseHandle(h)};t.Fatal("mismatched WAL admitted")}
 t.Setenv("WBD_PLAN028_TWO_REAL_CLIENTS","0")
 global,e:=m0Plan028WindowsNativeClientSlot(a)
 if e!=nil{t.Fatal("legacy global singleton lost",e)}
 defer windows.CloseHandle(global)
 if dup,e:=m0Plan028WindowsNativeClientSlot(b);e==nil{if dup!=0{_ = windows.CloseHandle(dup)};t.Fatal("legacy second global owner admitted")}
 t.Log("H1381_TWO_REAL_WINDOWS_NAMED_KERNEL_EVENTS_ALIAS_BOUND_AND_OLD_SINGLETON_PRESERVED")
}
