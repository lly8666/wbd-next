//go:build windows && wbd_v4_embedded_go
package main

import (
 "errors"
 "net/netip"
 "path/filepath"
 "testing"
 "golang.org/x/sys/windows"
 "github.com/lly8666/wobuzhidao/internal/windowsclient"
)
func TestPLAN028H1515FiveOriginalWindowsNativeDeviceSlots(t *testing.T){
 t.Setenv("GITHUB_ACTIONS","true")
 t.Setenv("WBD_PLAN028_TWO_REAL_CLIENTS","0")
 t.Setenv("WBD_PLAN028_FIVE_REAL_CLIENTS","1")
 names:=[]string{"alice","bob","carol","dave","erin"}
 aliases:=[]string{"WBDWL5A0","WBDWL5B1","WBDWL5C2","WBDWL5D3","WBDWL5E4"}
 ip:=[]string{"10.66.0.2/32","10.66.0.3/32","10.66.0.4/32","10.66.0.5/32","10.66.0.6/32"}
 var opts [5]m0NativeV4Options
 var handles []windows.Handle
 defer func(){for _,h:=range handles{_ = windows.CloseHandle(h)}}()
 for i:=0;i<5;i++{
  opts[i]=m0NativeV4Options{
   AdapterAlias:aliases[i],Username:names[i],
   Lease4:netip.MustParsePrefix(ip[i]),
   StatePath:filepath.Join(t.TempDir(),"h1506-owned-"+names[i]+".json"),
  }
  h,e:=m0Plan028WindowsNativeClientSlot(opts[i])
  if e!=nil{t.Fatalf("distinct signed OS event /32 slot %s: %v",names[i],e)}
  handles=append(handles,h)
 }
 if h,e:=m0Plan028WindowsNativeClientSlot(opts[0]);e==nil||h!=0{
  if h!=0{_ = windows.CloseHandle(h)}
  t.Fatalf("duplicate physical device not fenced %v",e)
 }
 bad:=opts[1];bad.Username="alice"
 if h,e:=m0Plan028WindowsNativeClientSlot(bad);!errors.Is(e,windowsclient.ErrN4NativeGuard){
  if h!=0{_ = windows.CloseHandle(h)}
  t.Fatalf("foreign account could claim Bob's alias: %v",e)
 }
 bad=opts[1];bad.Lease4=netip.MustParsePrefix("10.66.0.4/32")
 if h,e:=m0Plan028WindowsNativeClientSlot(bad);!errors.Is(e,windowsclient.ErrN4NativeGuard){
  if h!=0{_ = windows.CloseHandle(h)}
  t.Fatalf("foreign /32 could claim Bob's adapter: %v",e)
 }
 bad=opts[1];bad.StatePath=filepath.Join(t.TempDir(),"h1506-owned-carol.json")
 if h,e:=m0Plan028WindowsNativeClientSlot(bad);!errors.Is(e,windowsclient.ErrN4NativeGuard){
  if h!=0{_ = windows.CloseHandle(h)}
  t.Fatalf("foreign WAL could claim Bob's adapter: %v",e)
 }
 bad=opts[1];bad.AdapterAlias="WBDWLCLIENTB"
 if h,e:=m0Plan028WindowsNativeClientSlot(bad);!errors.Is(e,windowsclient.ErrN4NativeGuard){
  if h!=0{_ = windows.CloseHandle(h)}
  t.Fatalf("two-client scoped alias leaked into five-client scope: %v",e)
 }
 t.Setenv("WBD_PLAN028_FIVE_REAL_CLIENTS","0")
 global,e:=m0Plan028WindowsNativeClientSlot(opts[0])
 if e!=nil{t.Fatal("production singleton not retained",e)}
 defer windows.CloseHandle(global)
 if h,e:=m0Plan028WindowsNativeClientSlot(opts[1]);e==nil{
  if h!=0{_ = windows.CloseHandle(h)}
  t.Fatal("legacy global machine singleton bypassed")
 }
 t.Log("H1515_FIVE_CI_ONLY_NAMED_NATIVE_OWNER_SLOTS_AND_GLOBAL_DEFAULT_PRESERVED")
}
