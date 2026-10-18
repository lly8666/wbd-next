//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_owner_probe
package realityfront

import (
    "testing"
)

// Actual original Go recognized TLS + password + private V4 reply, then
// original Go Detach/Commit Rust; NO synthetic cold constructor authority.
// The extra compile tag makes this test-only scope unavailable in production.
func TestR0V4Fec2ActualGoTLSEpochOwnerGrantScoped(t *testing.T){
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(string(rune('0'+cipher)),func(t *testing.T){
            store,err:=NewV4EpochStore(2)
            if err!=nil{t.Fatal(err)}
            base:=&v4EmbeddedNativeBridge{}
            c0,s0,ce,se:=v4PairWithPrivateBridgeCipher(t,base,store,cipher)
            if ce!=nil||se!=nil||!base.committed||c0==nil||s0==nil{
                t.Fatalf("default V4 owner failed: %v %v",ce,se)
            }
            if base.protectedFeatures!=v4RequiredFeatures ||
                base.fec2ProbeScope(s0.Epoch){
                t.Fatal("default authenticated V4 illegally received FEC2 owner permission")
            }
            if err:=base.stopRelease();err!=nil{t.Fatal(err)}
            if err:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),
                1,s0.Epoch);err!=nil{t.Fatal(err)}
            scoped:=&v4EmbeddedNativeBridge{}
            c,s,ce,se:=v4PairWithPrivateBridgeCipher(t,scoped,store,cipher,true)
            if ce!=nil||se!=nil||c==nil||s==nil||!scoped.committed {
                t.Fatalf("real TLS private FEC2 owner scope not installed: %v %v",ce,se)
            }
            if s.Epoch==s0.Epoch||s.Epoch==[16]byte{} ||
                scoped.handle==0||scoped.protectedFeatures!=7 ||
                scoped.protectedEpoch!=s.Epoch||
                !scoped.fec2ProbeScope(s.Epoch){
                t.Fatal("protected bit2 permission not bound to exact new epoch and generation")
            }
            var bad [16]byte
            bad[0]=s.Epoch[0]^0xff
            if scoped.fec2ProbeScope(bad)||scoped.fec2ProbeScope(s0.Epoch){
                t.Fatal("wrong or retired epoch inherited private FEC2 permission")
            }
            oldHandle:=scoped.handle
            if err:=scoped.stopRelease();err!=nil{t.Fatal(err)}
            if scoped.fec2ProbeScope(s.Epoch){
                t.Fatal("stopped FEC2 scope remained active")
            }
            if _,err:=v4EmbeddedNativeState(oldHandle);err==nil{
                t.Fatal("old generation still registered")
            }
            if err:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),
                1,s.Epoch);err!=nil{t.Fatal(err)}
        })
    }
}
