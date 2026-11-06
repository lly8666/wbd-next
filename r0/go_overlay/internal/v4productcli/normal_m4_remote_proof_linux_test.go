//go:build linux && cgo && wbd_v4_embedded_go

package v4productcli

import (
    "context"
    "errors"
    "testing"
    "time"

    "github.com/lly8666/wobuzhidao/internal/realityfront"
)

func TestPLAN028NormalM4AfterPeerRxFenceAndTimeout(t *testing.T){
    t.Run("actual_M4_RX_permits_single_route_promotion",func(t *testing.T){
        polls:=0
        promotions:=0
        pulse:=func()(realityfront.V4PublicLoopPulse,error){
            polls++
            if polls>=3{return realityfront.V4PublicLoopPulse{RxRecords:1},nil}
            return realityfront.V4PublicLoopPulse{},nil
        }
        err:=waitOriginalNormalM4PeerProof(context.Background(),pulse,func()error{
            promotions++
            return nil
        },time.Second)
        if err!=nil||promotions!=1||polls<3{
            t.Fatalf("actual authenticated RX failed to promote exactly once: polls=%d promos=%d err=%v",polls,promotions,err)
        }
    })
    t.Run("local_TLS_READY_without_remote_M4_keeps_old_route",func(t *testing.T){
        promotions:=0
        err:=waitOriginalNormalM4PeerProof(context.Background(),
            func()(realityfront.V4PublicLoopPulse,error){
                return realityfront.V4PublicLoopPulse{},nil
            },func()error{promotions++;return nil},35*time.Millisecond)
        if err==nil||promotions!=0{
            t.Fatalf("unproven remote M4 may never revoke old owner: err=%v promotes=%d",err,promotions)
        }
    })
    t.Run("native_terminal_or_cancel_fails_closed",func(t *testing.T){
        ran:=false
        err:=waitOriginalNormalM4PeerProof(context.Background(),
            func()(realityfront.V4PublicLoopPulse,error){
                return realityfront.V4PublicLoopPulse{AuthenticatedPeerDead:true},nil
            },func()error{ran=true;return nil},time.Second)
        if err==nil||ran{t.Fatal("native dead cannot promote old route")}
        ctx,cancel:=context.WithCancel(context.Background())
        cancel()
        err=waitOriginalNormalM4PeerProof(ctx,
            func()(realityfront.V4PublicLoopPulse,error){
                return realityfront.V4PublicLoopPulse{},nil
            },func()error{ran=true;return nil},time.Second)
        if !errors.Is(err,context.Canceled)||ran{
            t.Fatalf("canceled candidate cannot promote: %v",err)
        }
    })
}
