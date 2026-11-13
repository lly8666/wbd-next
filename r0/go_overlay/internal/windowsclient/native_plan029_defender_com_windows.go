//go:build windows

package windowsclient

// PLAN029 native Windows Defender INetFwPolicy2/INetFwRule adapter.
// No PowerShell, netsh, direct WFP injection, global profile toggle,
// wildcard address, wildcard port, external Go packet worker or fallback.
//
// This file provides an OS backend. The owner still MUST have a durable
// generation-specific intent before Add, and a confirmed owned sidecar
// before Delete. A COM readback is not by itself permission to delete.
import (
 "context"
 "fmt"
 "runtime"
 "strconv"
 "syscall"
 "unicode/utf16"
 "unsafe"

 "golang.org/x/sys/windows"
)

type n4Plan029DefenderCOM struct{}

type n4Plan029COMObject uintptr

var (
 n4Plan029Ole32=syscall.NewLazyDLL("ole32.dll")
 n4Plan029OleAut=syscall.NewLazyDLL("oleaut32.dll")
 n4Plan029CoInit=n4Plan029Ole32.NewProc("CoInitializeEx")
 n4Plan029CoUninit=n4Plan029Ole32.NewProc("CoUninitialize")
 n4Plan029CoCreate=n4Plan029Ole32.NewProc("CoCreateInstance")
 n4Plan029SysAlloc=n4Plan029OleAut.NewProc("SysAllocString")
 n4Plan029SysFree=n4Plan029OleAut.NewProc("SysFreeString")
 n4Plan029SysLen=n4Plan029OleAut.NewProc("SysStringLen")
)
type n4Plan029COMError uint32
func(e n4Plan029COMError)Error()string{
 return fmt.Sprintf("Defender native COM HRESULT 0x%08x",uint32(e))
}
func n4Plan029HRESULT(hr uintptr)error{
 if int32(uint32(hr))>=0{return nil}
 return n4Plan029COMError(uint32(hr))
}
func(o n4Plan029COMObject) call(idx uintptr,args ...uintptr)error{
 if o==0||idx>42{return ErrN4NativeGuard}
 vt:=*(*uintptr)(unsafe.Pointer(uintptr(o)))
 if vt==0{return ErrN4NativeGuard}
 proc:=*(*uintptr)(unsafe.Pointer(vt+idx*unsafe.Sizeof(uintptr(0))))
 if proc==0{return ErrN4NativeGuard}
 argv:=append([]uintptr{uintptr(o)},args...)
 hr,_,_:=syscall.SyscallN(proc,argv...)
 return n4Plan029HRESULT(hr)
}
func(o n4Plan029COMObject) release(){
 if o!=0{_ = o.call(2)}
}
func n4Plan029BSTR(s string)(uintptr,error){
 if len(s)>1024{return 0,ErrN4NativeGuard}
 u,e:=syscall.UTF16FromString(s);if e!=nil{return 0,e}
 ptr,_,_:=n4Plan029SysAlloc.Call(uintptr(unsafe.Pointer(&u[0])))
 runtime.KeepAlive(u)
 if ptr==0{return 0,ErrN4NativeGuard}
 return ptr,nil
}
func(o n4Plan029COMObject) setString(idx uintptr,s string)error{
 b,e:=n4Plan029BSTR(s);if e!=nil{return e}
 defer n4Plan029SysFree.Call(b)
 return o.call(idx,b)
}
func(o n4Plan029COMObject) getString(idx uintptr)(string,error){
 var str uintptr
 if e:=o.call(idx,uintptr(unsafe.Pointer(&str)));e!=nil{return "",e}
 if str==0{return "",nil}
 defer n4Plan029SysFree.Call(str)
 n,_,_:=n4Plan029SysLen.Call(str)
 if n>4096{return "",ErrN4NativeGuard}
 return string(utf16.Decode(unsafe.Slice((*uint16)(unsafe.Pointer(str)),int(n)))),nil
}
func(o n4Plan029COMObject) getInt(idx uintptr)(int32,error){
 var value int32
 if e:=o.call(idx,uintptr(unsafe.Pointer(&value)));e!=nil{return 0,e}
 return value,nil
}
func(o n4Plan029COMObject) getBool(idx uintptr)(bool,error){
 var value int16
 if e:=o.call(idx,uintptr(unsafe.Pointer(&value)));e!=nil{return false,e}
 return value!=0,nil
}
func n4Plan029WithCOM(ctx context.Context,fn func(n4Plan029COMObject)error)error{
 if ctx==nil{return ErrN4NativeGuard}
 if e:=ctx.Err();e!=nil{return e}
 runtime.LockOSThread()
 defer runtime.UnlockOSThread()
 hr,_,_:=n4Plan029CoInit.Call(0,2) // COINIT_APARTMENTTHREADED
 if e:=n4Plan029HRESULT(hr);e!=nil{return e}
 defer n4Plan029CoUninit.Call()
 g,err:=windows.GUIDFromString("{E2B3C97F-6AE1-41AC-817A-F6F92166D7DD}")
 if err!=nil{return err}
 iid,err:=windows.GUIDFromString("{98325047-C671-4174-8D81-DEFCD3F03186}")
 if err!=nil{return err}
 var policy uintptr
 hr,_,_=n4Plan029CoCreate.Call(uintptr(unsafe.Pointer(&g)),0,1,
  uintptr(unsafe.Pointer(&iid)),uintptr(unsafe.Pointer(&policy)))
 if e:=n4Plan029HRESULT(hr);e!=nil{return e}
 if policy==0{return ErrN4NativeGuard}
 defer n4Plan029COMObject(policy).release()
 var rules uintptr
 if e:=n4Plan029COMObject(policy).call(18,uintptr(unsafe.Pointer(&rules)));e!=nil{return e}
 if rules==0{return ErrN4NativeGuard}
 defer n4Plan029COMObject(rules).release()
 return fn(n4Plan029COMObject(rules))
}
func n4Plan029COMItem(rules n4Plan029COMObject,name string)(n4Plan029COMObject,bool,error){
 b,e:=n4Plan029BSTR(name);if e!=nil{return 0,false,e}
 defer n4Plan029SysFree.Call(b)
 var rule uintptr
 err:=rules.call(10,b,uintptr(unsafe.Pointer(&rule)))
 if err!=nil{
  // Only the exact HRESULT_FROM_WIN32(ERROR_FILE_NOT_FOUND)
  // means absent; never normalize ACCESS_DENIED or foreign errors.
  if err==n4Plan029COMError(0x80070002){return 0,false,nil}
  return 0,false,err
 }
 if rule==0{return 0,false,ErrN4NativeGuard}
 return n4Plan029COMObject(rule),true,nil
}
func n4Plan029ExactRule(obj n4Plan029COMObject,k n4Plan029DefenderKey)(bool,error){
 strings:=[]struct{idx uintptr;value string}{
  {7,k.Name},{9,k.Description},
  {17,strconv.Itoa(int(k.Port))},
  {21,k.Lease4.String()},{23,k.Remote4.String()},
 }
 for _,v:=range strings{
  actual,e:=obj.getString(v.idx)
  if e!=nil{return false,e}
  if actual!=v.value{return false,nil}
 }
 ints:=[]struct{idx uintptr;value int32}{
  {15,6}, // TCP only
  {27,1}, // inbound only
  {37,7}, // domain/private/public, still exact IP/port
  {41,1}, // allow
 }
 for _,v:=range ints{
  actual,e:=obj.getInt(v.idx)
  if e!=nil{return false,e}
  if actual!=v.value{return false,nil}
 }
 enabled,e:=obj.getBool(33);if e!=nil{return false,e}
 edge,e:=obj.getBool(39);if e!=nil{return false,e}
 return enabled&&!edge,nil
}
func (n4Plan029DefenderCOM)Lookup(ctx context.Context,k n4Plan029DefenderKey)(
 present,exact bool,err error){
 if err=k.validate();err!=nil{return false,false,err}
 err=n4Plan029WithCOM(ctx,func(rules n4Plan029COMObject)error{
  obj,found,e:=n4Plan029COMItem(rules,k.Name)
  if e!=nil{return e}
  if !found{return nil}
  defer obj.release()
  present=true
  exact,e=n4Plan029ExactRule(obj,k)
  return e
 })
 return
}
func (n4Plan029DefenderCOM)CreateIfAbsent(ctx context.Context,k n4Plan029DefenderKey)error{
 if e:=k.validate();e!=nil{return e}
 return n4Plan029WithCOM(ctx,func(rules n4Plan029COMObject)error{
  obj,present,e:=n4Plan029COMItem(rules,k.Name)
  if e!=nil{return e}
  if present{obj.release();return ErrN4ForeignRoute}
  clsid,e:=windows.GUIDFromString("{2C5BC43E-3369-4C33-AB0C-BE9469677AF4}")
  if e!=nil{return e}
  iid,e:=windows.GUIDFromString("{AF230D27-BABA-4E42-ACED-F524F22CFCE2}")
  if e!=nil{return e}
  var raw uintptr
  hr,_,_:=n4Plan029CoCreate.Call(uintptr(unsafe.Pointer(&clsid)),0,1,
   uintptr(unsafe.Pointer(&iid)),uintptr(unsafe.Pointer(&raw)))
  if e:=n4Plan029HRESULT(hr);e!=nil{return e}
  if raw==0{return ErrN4NativeGuard}
  rule:=n4Plan029COMObject(raw)
  defer rule.release()
  if e=rule.setString(8,k.Name);e!=nil{return e}
  if e=rule.setString(10,k.Description);e!=nil{return e}
  if e=rule.call(16,6);e!=nil{return e} // protocol before ports
  if e=rule.setString(18,strconv.Itoa(int(k.Port)));e!=nil{return e}
  if e=rule.setString(22,k.Lease4.String());e!=nil{return e}
  if e=rule.setString(24,k.Remote4.String());e!=nil{return e}
  if e=rule.call(28,1);e!=nil{return e} // IN
  if e=rule.call(38,7);e!=nil{return e} // only IP/port precise
  if e=rule.call(40,0);e!=nil{return e} // no edge traversal
  if e=rule.call(42,1);e!=nil{return e} // allow, never Block
  if e=rule.call(34,0xffff);e!=nil{return e} // VARIANT_TRUE
  if e=rules.call(8,raw);e!=nil{return e}
  got,found,e:=n4Plan029COMItem(rules,k.Name)
  if e!=nil{return e}
  if !found{return ErrN4RouteAmbiguous}
  defer got.release()
  exact,e:=n4Plan029ExactRule(got,k)
  if e!=nil{return e}
  if !exact{return ErrN4RouteAmbiguous}
  return nil
 })
}
func (n4Plan029DefenderCOM)RemoveOwned(ctx context.Context,k n4Plan029DefenderKey)error{
 if e:=k.validate();e!=nil{return e}
 return n4Plan029WithCOM(ctx,func(rules n4Plan029COMObject)error{
  got,found,e:=n4Plan029COMItem(rules,k.Name)
  if e!=nil{return e}
  if !found{return nil}
  exact,e:=n4Plan029ExactRule(got,k)
  got.release()
  if e!=nil{return e}
  if !exact{return ErrN4ForeignRoute}
  b,e:=n4Plan029BSTR(k.Name);if e!=nil{return e}
  defer n4Plan029SysFree.Call(b)
  if e=rules.call(9,b);e!=nil{return e}
  // Never report Stop when an exact live rule remains after mutation.
  rule,present,e:=n4Plan029COMItem(rules,k.Name)
  if present{rule.release()}
  if e!=nil{return e}
  if present{return ErrN4RouteAmbiguous}
  return nil
 })
}
