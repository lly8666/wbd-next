//go:build linux && cgo && wbd_v4_embedded_go
package v4productcli
import (
    "testing"
    "github.com/lly8666/wobuzhidao/internal/realityfront"
)
func TestPlan027NativeColdReconnectOnlyOnAuthenticated90sDead(t *testing.T){
    for _,p:=range []realityfront.V4PublicLoopPulse{
        {TxErrors:1,TxRecords:32},
        {TxErrors:500,TxRecords:1500,RxErrors:17},
        {TxRecords:10,RxErrors:1},
    } {
        if publicNativeHealthDead(p){
            t.Fatal("transient local kernel error triggered cold TLS reconnect")
        }
    }
    if !publicNativeHealthDead(realityfront.V4PublicLoopPulse{
        AuthenticatedPeerDead:true,TxErrors:1}){
        t.Fatal("actual Rust authenticated peer Health timeout must reconnect")
    }
}
