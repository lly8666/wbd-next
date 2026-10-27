//go:build windows && wbd_v4_embedded_go
package main
import (
 "os"
 "testing"
)

func TestM0PLAN023WindowsRustNativeModeABIRejectsUntrustedLibrary(t *testing.T){
 for _,mode:=range []m0WindowsV4Mode{m0WinModeNormal,m0WinModeFixed,m0WinModeAuto,m0WinModeGame2,m0WinModeGame4}{
  if err:=m0CheckWindowsV4NativeMode(mode,"wbd_engine.dll");err==nil {t.Errorf("relative DLL path admitted mode=%s",mode)}
 }
 if err:=m0CheckWindowsV4NativeMode("not-a-mode","C:\\invalid\\wbd_engine.dll");err==nil {t.Fatal("unrecognized mode accepted")}
}

func TestM0PLAN024WindowsNativeWholeProductCapabilityGate(t *testing.T){
 // CI must supply the absolute SAME SOURCE native Rust DLL. This is a
 // read-only capability/Go selector check, before Npcap/Wintun/WFP.
 // Missing optional local DLL is NOT a product test PASS.
 library:=os.Getenv("WBD_M0_TEST_NATIVE_V4_DLL")
 if library==""{t.Skip("no same-source native DLL; public product gate NOT_RUN")}
 for _,mode:=range []m0WindowsV4Mode{
  m0WinModeNormal,m0WinModeFixed,m0WinModeAuto,
  m0WinModeGame2,m0WinModeGame4,
 }{
  if err:=m0CheckWindowsV4NativeMode(mode,library);err!=nil{
   t.Fatalf("native Rust original Game/FEC2 candidate missing mode=%s: %v",mode,err)
  }
 }
 // DLL capability alone cannot claim public Game/Auto PASS: exact
 // original-Go 2/4 NPF+TLS/Wintun+Stop E2E runs separately below.
}
