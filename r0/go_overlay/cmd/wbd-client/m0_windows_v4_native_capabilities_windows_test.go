//go:build windows && wbd_v4_embedded_go
package main
import "testing"

func TestM0PLAN023WindowsRustNativeModeABIRejectsUntrustedLibrary(t *testing.T){
 for _,mode:=range []m0WindowsV4Mode{m0WinModeNormal,m0WinModeFixed,m0WinModeAuto,m0WinModeGame2,m0WinModeGame4}{
  if err:=m0CheckWindowsV4NativeMode(mode,"wbd_engine.dll");err==nil {t.Errorf("relative DLL path admitted mode=%s",mode)}
 }
 if err:=m0CheckWindowsV4NativeMode("not-a-mode","C:\\invalid\\wbd_engine.dll");err==nil {t.Fatal("unrecognized mode accepted")}
}
