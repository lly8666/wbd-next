//go:build windows && wbd_v4_embedded_go
package realityfront

import (
 "errors"
 "testing"
)

// Regression for S45 original Windows/Linux Auto: the real opener's
// presentation layer must retain the typed INVALID(1) rejection rather
// than convert it into a fatal owner failure via fmt.Errorf rc=%v.
func TestM0WindowsFEC2OpenABICodeClassificationSurvivesWrapper(t *testing.T){
 for _,tc:=range []struct{code uintptr;fatal bool}{
  {1,false},{2,true},{3,true},{4,true},{5,true},
 }{
  err:=winFec2OpenCallStatus(0,&v4WindowsNativeABIError{Code:tc.code})
  var status *v4WindowsNativeABIError
  if !errors.As(err,&status)||status.Code!=tc.code{
   t.Fatalf("FEC2 rc=%d lost typed provenance: %v",tc.code,err)
  }
  if !errors.Is(err,errV4WindowsOwner){
   t.Fatalf("FEC2 rc=%d lost owner source: %v",tc.code,err)
  }
  if got:=V4WindowsNativeOwnerFatal(err);got!=tc.fatal{
   t.Fatalf("FEC2 rc=%d fatal=%v want=%v",tc.code,got,tc.fatal)
  }
 }
 if err:=winFec2OpenCallStatus(16,nil);err!=nil{
  t.Fatalf("valid FEC2 maximum delivery count rejected: %v",err)
 }
 if err:=winFec2OpenCallStatus(17,nil);err==nil||!V4WindowsNativeOwnerFatal(err){
  t.Fatalf("out-of-range FEC2 count did not fail closed: %v",err)
 }
 if err:=winFec2OpenCallStatus(0,errV4WindowsOwner);err==nil||!V4WindowsNativeOwnerFatal(err){
  t.Fatalf("untyped FEC2 owner failure was hidden: %v",err)
 }
}

func TestM0WindowsNormalOpenFirstFaultTypedABIAndOutput(t *testing.T){
 for _,tc:=range []struct{rc uintptr;fatal bool}{{1,false},{2,true},{3,true},{4,true},{5,true}}{
  err:=winNormalV4OpenStatus(&v4WindowsNativeABIError{Code:tc.rc},64,0,0,0)
  var abi *v4WindowsNativeABIError
  if !errors.As(err,&abi)||abi.Code!=tc.rc||!errors.Is(err,errV4WindowsOwner)||V4WindowsNativeOwnerFatal(err)!=tc.fatal{
   t.Fatalf("Normal opener rc=%d loses typed status/fatal classification: %v",tc.rc,err)
  }
 }
 for _,v:=range []struct{used uintptr;kind uint32;head byte;ok bool}{
  {20,1,0x45,true},{0,2,0,true},{64,1,0x45,false},
  {19,1,0x45,false},{20,3,0x45,false},{20,1,0x65,false},
 }{
  err:=winNormalV4OpenStatus(nil,60,v.used,v.kind,v.head)
  if (err==nil)!=v.ok{t.Fatalf("Normal malformed output used=%d kind=%d got=%v",v.used,v.kind,err)}
  if err!=nil&&!V4WindowsNativeOwnerFatal(err){t.Fatalf("malformed native output must fail closed: %v",err)}
 }
}
