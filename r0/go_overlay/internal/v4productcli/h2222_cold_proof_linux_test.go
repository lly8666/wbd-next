//go:build linux && cgo && wbd_v4_embedded_go
package v4productcli

import (
 "context"
 "errors"
 "sync/atomic"
 "testing"
 "time"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
)
// H2222: a real 45s overlap budget is shared by the client and server
// original-Go supervisors. A zero-business candidate MUST NOT be promoted
// by local TLS or a plain socket condition, and cancel beats any deadline.
func TestH2222ColdNativeCandidateBudgetAndAuthOnlyPromotion(t *testing.T){
 if originalNativeM4ColdProofBudget!=45*time.Second{
  t.Fatalf("client/server M4 overlap must cover one 45s cold challenge window: %s",originalNativeM4ColdProofBudget)
 }
 for _,server:=range []bool{false,true}{
  t.Run(map[bool]string{false:"client",true:"server"}[server],func(t *testing.T){
   var promoted atomic.Int32
   pulse:=func()(realityfront.V4PublicLoopPulse,error){return realityfront.V4PublicLoopPulse{},nil}
   promote:=func()error{promoted.Add(1);return nil}
   ctx,cancel:=context.WithCancel(context.Background())
   cancel()
   var err error
   if server{
    err=waitOriginalNativeServerClientM4Ready(ctx,pulse,promote,originalNativeM4ColdProofBudget)
   }else{
    err=waitOriginalNativeM4PeerProof(ctx,pulse,promote,originalNativeM4ColdProofBudget)
   }
   if !errors.Is(err,context.Canceled)||promoted.Load()!=0{
    t.Fatalf("cold canceled candidate cannot grant route: %v promoted=%d",err,promoted.Load())
   }
   deadline:=20*time.Millisecond
   if server{
    err=waitOriginalNativeServerClientM4Ready(context.Background(),pulse,promote,deadline)
   }else{
    err=waitOriginalNativeM4PeerProof(context.Background(),pulse,promote,deadline)
   }
   if err==nil||promoted.Load()!=0{
    t.Fatalf("zero authenticated M3 evidence must never pass candidate route: %v",err)
   }
  })
 }
}
