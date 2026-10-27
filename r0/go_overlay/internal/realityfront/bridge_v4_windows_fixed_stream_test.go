//go:build windows && wbd_v4_embedded_go
package realityfront

import (
    "syscall"
    "testing"
)

func TestM0RemediationWindowsNativeFixedProcSingleSessionCache(t *testing.T){
    dll,err:=syscall.LoadDLL("kernel32.dll")
    if err!=nil{t.Fatal(err)}
    defer dll.Release()
    b:=&v4WindowsNativeOwnerBridge{dll:dll}
    first,err:=b.fixedProc("GetCurrentProcessId")
    if err!=nil||first==nil{t.Fatalf("first real DLL resolution %v",err)}
    next,err:=b.fixedProc("GetCurrentProcessId")
    if err!=nil||first!=next{t.Fatal("session repeatedly resolves same symbol")}
    if _,err=b.fixedProc("WBD_MISSING_NATIVE_ABI_NEVER_EXISTS");err==nil{
        t.Fatal("missing API did not fail closed")
    }
}
