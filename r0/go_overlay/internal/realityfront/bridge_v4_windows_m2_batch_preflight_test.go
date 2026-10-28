//go:build windows && wbd_v4_embedded_go
package realityfront

import(
 "errors"
 "strings"
 "testing"
)

func TestM0PLAN025WindowsOriginalM2BatchPreflightClassifiesFirstRefusal(t *testing.T){
 a:=V4WindowsM2FirstsendResult{PN:7,Seq:100,WireLen:141,Outcome:1}
 b:=V4WindowsM2FirstsendResult{PN:8,Seq:241,WireLen:89,Outcome:2}
 cases:=[]struct{
  name string
  rows []V4WindowsM2FirstsendResult
  expected string
 }{
  {"valid",[]V4WindowsM2FirstsendResult{a,b},""},
  {"empty",nil,"M2_BATCH_BAD_COUNT"},
  {"bad-length",[]V4WindowsM2FirstsendResult{{PN:7,Seq:100,WireLen:30,Outcome:1}},"M2_BATCH_BAD_DESCRIPTOR"},
  {"bad-outcome",[]V4WindowsM2FirstsendResult{{PN:7,Seq:100,WireLen:141,Outcome:3}},"M2_BATCH_BAD_DESCRIPTOR"},
  {"noncontiguous",[]V4WindowsM2FirstsendResult{a,{PN:8,Seq:242,WireLen:89,Outcome:1}},"M2_BATCH_NONCONTIGUOUS"},
  {"duplicate-pn",[]V4WindowsM2FirstsendResult{a,{PN:7,Seq:241,WireLen:89,Outcome:1}},"M2_BATCH_DUPLICATE_PN"},
  {"serial-wrap",[]V4WindowsM2FirstsendResult{{PN:10,Seq:^uint32(0)-30,WireLen:100,Outcome:1},{PN:11,Seq:69,WireLen:89,Outcome:1}},""},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   err:=validateOriginalM2FirstsendBatch(tc.rows)
   if tc.expected==""{
    if err!=nil{t.Fatal(err)}
    return
   }
   if !errors.Is(err,errV4WindowsOwner)||!strings.Contains(err.Error(),tc.expected){
    t.Fatalf("preflight first reason lost: %v",err)
   }
  })
 }
}
