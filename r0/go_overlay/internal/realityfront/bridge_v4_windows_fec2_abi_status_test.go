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
