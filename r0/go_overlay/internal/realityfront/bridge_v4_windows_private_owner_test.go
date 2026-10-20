//go:build windows && wbd_v4_embedded_go
package realityfront

import (
    "errors"
    "os"
    "testing"
)
func TestM0WindowsOriginalGoRealCredentialTLSProtectedRustOwnerStopOnly(t *testing.T){
    lib:=os.Getenv("WBD_M0_WIN_OWNER_DLL")
    if lib==""{t.Fatal("missing exact native Rust Windows DLL; NOT_RUN must never look PASS")}
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(string(rune('0'+cipher)),func(t *testing.T){
            b,err:=newV4WindowsPrivateOwnerBridge(lib)
            if err!=nil{t.Fatal(err)}
            if _,ok:=any(b).(V4OriginalOwnerStopper);ok{
                t.Fatal("Rust-only Stop cannot become a Windows M4 OS product Stop receipt")
            }
            if err:=b.stopRustOwnerOnly();!errors.Is(err,errV4WindowsOwner){
                t.Fatalf("uncommitted owner cannot Stop as success: %v",err)
            }
            store,err:=NewV4EpochStore(1)
            if err!=nil{t.Fatal(err)}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,b,store,cipher)
            if ce!=nil||se!=nil||client==nil||server==nil||
                !b.committed||b.handle==0{
                t.Fatalf("real original-Go credential TLS -> Windows native Rust owner not committed: client=%v server=%v",ce,se)
            }
            st,err:=b.state()
            if err!=nil||st.phase!=2||st.loansDrained!=0||st.applied!=0||
                st.server!=1||st.generation==0 {
                t.Fatalf("trusted prepared Rust owner readback not exact or falsely applied: %+v err=%v",st,err)
            }
            h:=b.handle
            if err:=b.stopRustOwnerOnly();err!=nil{t.Fatal(err)}
            if err:=b.stopRustOwnerOnly();err!=nil{t.Fatal("repeat Rust Stop",err)}
            if b.handle!=0||b.committed||!b.stopped{t.Fatal("unreleased native owner")}
            if _,err:=b.state();!errors.Is(err,errV4WindowsOwner){
                t.Fatalf("retired token must be unavailable: %v",err)
            }
            if h==0{t.Fatal("no original protected generation allocated")}
            if err:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);err!=nil{
                t.Fatal("original Go epoch cleanup",err)
            }
        })
    }
}
func TestM0WindowsOriginalGoPrivateCallbackInvalidBeforeAuthenticatedTLS(t *testing.T){
    lib:=os.Getenv("WBD_M0_WIN_OWNER_DLL")
    if lib==""{t.Fatal("native DLL not connected")}
    b,e:=newV4WindowsPrivateOwnerBridge(lib)
    if e!=nil{t.Fatal(e)}
    if _,err:=b.prepare(V4ColdSessionSnapshot{},1,v4PeerTransport{});!errors.Is(err,errV4WindowsOwner){
        t.Fatalf("untrusted cold bytes acquired native owner: %v",err)
    }
    if b.handle!=0||b.committed||b.stopped {t.Fatal("unauthorized early owner created")}
}
