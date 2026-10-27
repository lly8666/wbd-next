//go:build windows
package main

import (
 "flag"
 "testing"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
 "github.com/lly8666/wobuzhidao/internal/runtimeentry"
)

// Keep BOTH frozen Linux namespaces: original credential-TLS V3 fixed4
// admission first; the Rust FEC2 Maximum6 codec is never a Go policy value.
func TestM0PLAN024WindowsFixed6OriginalGoAdmissionBeforeNative(t *testing.T){
 p,err:=realityfront.PolicyForClientWithInitialAndCipher(
  1,"fixed",4,4,20,realityfront.CipherChaCha)
 if err!=nil {t.Fatalf("original pinned Go V3 Fixed4 admission: %v",err)}
 if p.FECMode!=realityfront.FECFixed||p.FixedParity!=4||
  p.DesiredLanes!=1||p.Cipher!=realityfront.CipherChaCha{
  t.Fatalf("original TLS V3 fixed envelope mismatch: %+v",p)
 }
 opts:=flag.NewFlagSet("fixed6",flag.ContinueOnError)
 fec2:=runtimeentry.RegisterFEC2ProductFlags(opts)
 if e:=opts.Parse([]string{"--fec.mode=fixed","--fec.profile=maximum"});e!=nil {
  t.Fatalf("native FEC2 operator flags: %v",e)
 }
 if e:=fec2.Validate(1);e!=nil{t.Fatalf("native fixed6 profile admission: %v",e)}
 if got,e:=m0ParseWindowsV4Mode(1,*fec2.Mode,"fixed",4);e!=nil||got!=m0WinModeFixed{
  t.Fatalf("fixed6 after Go V3+FEC2 preflight got=%s err=%v",got,e)
 }
 if e:=opts.Set("fec.profile","strong");e!=nil{t.Fatal(e)}
 if e:=fec2.Validate(1);e!=nil{t.Fatalf("shared Linux FixedStream must permit Strong5: %v",e)}
 // Old broken harness must be rejected rather than masquerade as Applied.
 if _,e:=realityfront.PolicyForClientWithInitialAndCipher(
  1,"fixed",0,4,20,realityfront.CipherChaCha);e==nil{
  t.Fatal("original Go incorrectly accepted fixed0")
 }
}
func TestM0PLAN023WindowsNativeV4FiveModes(t *testing.T){
 cases:=[]struct{lanes int;fec2,legacy string;parity int;want m0WindowsV4Mode}{
  {1,"off","off",0,m0WinModeNormal},
  {1,"fixed","fixed",4,m0WinModeFixed},
  {1,"auto","auto",0,m0WinModeAuto},
  {2,"off","off",0,m0WinModeGame2},
  {4,"off","off",0,m0WinModeGame4},
  {2,"fixed","off",0,m0WinModeGame2},
  {4,"fixed","off",0,m0WinModeGame4},
 }
 // Native V4 parser must also honor original legacy/off empty-context tests;
 // independent Rust capability gate still rejects unfinished Auto/Game.
 for _,tc:=range cases{
  legacy:=tc.legacy
  if tc.fec2=="auto" {legacy="legacy"} // auto policy is not owned by Fixed parser
  got,err:=m0ParseWindowsV4Mode(tc.lanes,tc.fec2,legacy,tc.parity)
  if err!=nil||got!=tc.want{t.Errorf("lanes=%d mode=%s GoV3=%s parity=%d got=%s err=%v",
    tc.lanes,tc.fec2,legacy,tc.parity,got,err)}
 }
 invalid:=[]struct{lanes int;fec2,legacy string;parity int}{
  {3,"off","legacy",0},

  {4,"auto","legacy",0},
  {1,"off","auto",0},
  {1,"off","legacy",4},
  {1,"fixed","legacy",0},
  {1,"fixed","fixed",0},
  {1,"fixed","fixed",8},
  {1,"fixed","legacy",4},
  {1,"auto","fixed",4},
  {1,"bad","legacy",0},
 }
 for _,tc:=range invalid{
  if got,err:=m0ParseWindowsV4Mode(tc.lanes,tc.fec2,tc.legacy,tc.parity);err==nil{
   t.Errorf("invalid mode accepted %v: %s",tc,got)
  }
 }
}
