//go:build windows && wbd_v4_embedded_go
package realityfront

import(
 "errors"
 "strings"
 "testing"
)

func TestM0PLAN025WindowsNativeNormalOpenFirstFaultIsBoundedAndSafe(t *testing.T){
 good:=make([]byte,120);good[0]=0x45
 if err:=normalOpenVerifiedKind1(1,120,good);err!=nil{t.Fatal(err)}
 cases:=[]struct{name string;kind uint32;used uintptr;first byte;fatal bool;stage string}{
  {"unexpected-kind",3,120,0x45,true,"NORMAL_OPEN_UNEXPECTED_KIND"},
  {"empty-accepted-data",1,0,0x45,false,"NORMAL_OPEN_AUTHENTICATED_IPV4_SHORT"},
  {"wrong-IP-version",1,120,0x65,false,"NORMAL_OPEN_AUTHENTICATED_IPV4_HEADER"},
  {"short-IHL",1,120,0x44,false,"NORMAL_OPEN_AUTHENTICATED_IPV4_HEADER"},
  {"IHL-exceeds-plaintext",1,20,0x4f,false,"NORMAL_OPEN_AUTHENTICATED_IPV4_HEADER"},
  {"output-overflow",1,121,0x45,true,"NORMAL_OPEN_OUTPUT_OVERFLOW"},
 }
 for _,tc:=range cases{
  t.Run(tc.name,func(t *testing.T){
   p:=make([]byte,120);p[0]=tc.first
   err:=normalOpenVerifiedKind1(tc.kind,tc.used,p)
   if err==nil||!errors.Is(err,errV4WindowsOwner)||
      !strings.Contains(err.Error(),tc.stage)||
      V4WindowsNativeOwnerFatal(err)!=tc.fatal{
    t.Fatalf("unsafe Normal M3 classification: %v fatal=%v expected=%v",err,V4WindowsNativeOwnerFatal(err),tc.fatal)
   }
  })
 }
}
