//go:build linux && cgo && wbd_v4_embedded_go
package realityfront
import "testing"
func TestR0V4EmbeddedNativeProtectedControlAllCiphers(t *testing.T){
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(string(rune('0'+cipher)),func(t *testing.T){
            store,err:=NewV4EpochStore(1);if err!=nil{t.Fatal(err)}
            b:=&v4EmbeddedNativeBridge{}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,b,store,cipher)
            if ce!=nil||se!=nil||client==nil||server==nil||
               !b.committed||b.handle==0{
                t.Fatalf("real Go protected TLS embedded Rust commit: client=%v server=%v",ce,se)
            }
            state,err:=b.state()
            if err!=nil||state!=2{t.Fatalf("owner phase=%d err=%v",state,err)}
            if err:=b.stopRelease();err!=nil{t.Fatal(err)}
            if _,err:=b.state();err==nil{t.Fatal("released owner still visible")}
            if err:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,server.Epoch);err!=nil{t.Fatal(err)}
        })
    }
}
