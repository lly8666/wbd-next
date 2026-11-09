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
        err:=waitOriginalNativeM4PeerProof(context.Background(),pulse,func()error{
            promotions++
            return nil
        },time.Second)
        if err!=nil||promotions!=1||polls<3{
            t.Fatalf("actual authenticated RX failed to promote exactly once: polls=%d promos=%d err=%v",polls,promotions,err)
        }
    })
    t.Run("authenticated_native_Normal_or_Game_health_without_reverse_IP_proves_remote_commit",func(t *testing.T){
        promotions:=0
        pulses:=0
        err:=waitOriginalNativeM4PeerProof(context.Background(),
            func()(realityfront.V4PublicLoopPulse,error){
                pulses++
                // Merely local M4 started and raw TCP ACK must never be
                // interpreted as a cryptographic remote commit receipt.
                if pulses<3{return realityfront.V4PublicLoopPulse{},nil}
                return realityfront.V4PublicLoopPulse{
                    RxRecords:0,AuthenticatedPeerControl:true,
                },nil
            },
            func()error{promotions++;return nil},time.Second)
        if err!=nil||promotions!=1||pulses!=3{
            t.Fatalf("canonical Normal/Game native control did not promote exact route once: err=%v promotions=%d pulses=%d",err,promotions,pulses)
        }
    })
    t.Run("local_TLS_READY_without_remote_M4_keeps_old_route",func(t *testing.T){
        promotions:=0
        err:=waitOriginalNativeM4PeerProof(context.Background(),
            func()(realityfront.V4PublicLoopPulse,error){
                return realityfront.V4PublicLoopPulse{},nil
            },func()error{promotions++;return nil},35*time.Millisecond)
        if err==nil||promotions!=0{
            t.Fatalf("unproven remote M4 may never revoke old owner: err=%v promotes=%d",err,promotions)
        }
    })
    t.Run("native_terminal_or_cancel_fails_closed",func(t *testing.T){
        ran:=false
        err:=waitOriginalNativeM4PeerProof(context.Background(),
            func()(realityfront.V4PublicLoopPulse,error){
                return realityfront.V4PublicLoopPulse{AuthenticatedPeerDead:true},nil
            },func()error{ran=true;return nil},time.Second)
        if err==nil||ran{t.Fatal("native dead cannot promote old route")}
        ctx,cancel:=context.WithCancel(context.Background())
        cancel()
        err=waitOriginalNativeM4PeerProof(ctx,
            func()(realityfront.V4PublicLoopPulse,error){
                return realityfront.V4PublicLoopPulse{},nil
            },func()error{ran=true;return nil},time.Second)
        if !errors.Is(err,context.Canceled)||ran{
            t.Fatalf("canceled candidate cannot promote: %v",err)
        }
    })
}

func TestPLAN028NormalHealthPreterminalStartsOneColdIntentWithoutStoppingLiveA(t *testing.T){
    ctx,cancel:=context.WithCancel(context.Background())
    defer cancel()
    notify:=make(chan struct{},1)
    done:=make(chan error,1)
    polls:=0
    go func(){
        done<-monitorPublicNativePeer(ctx,make(chan error),
            func()bool{return true},
            func()(realityfront.V4PublicLoopPulse,error){
                polls++
                // Only the original M4 authenticated last-receipt
                // age may request a preterminal Cold B. The terminal
                // 90s Health flag remains separate and false.
                return realityfront.V4PublicLoopPulse{
                    AuthenticatedPeerPreDead:true,
                    AuthenticatedPeerDead:false,
                },nil
            },notify)
    }()
    select{
    case <-notify:
    case <-time.After(2500*time.Millisecond):
        t.Fatal("real native authenticated preterminal health was not signaled")
    }
    select{
    case err:=<-done:t.Fatalf("stale-but-not-dead stopped active A: %v",err)
    default:
    }
    cancel()
    select{
    case err:=<-done:
        if err!=nil{t.Fatalf("client Stop returned error: %v",err)}
    case <-time.After(2*time.Second):t.Fatal("native monitor did not respect owned Stop")
    }
    if polls!=1{t.Fatalf("preterminal refresh emitted multiple Go cold requests: polls=%d",polls)}
    select{
    case <-notify:t.Fatal("preterminal generation signaled twice")
    default:
    }
}

func TestPLAN028ServerBNeedsAuthenticatedClientNativeHealthNotJustUplink(t *testing.T){
    t.Run("B_native_RX_or_local_start_without_authenticated_client_Health_keeps_A",func(t *testing.T){
        promotions:=0
        err:=waitOriginalNativeServerClientM4Ready(context.Background(),
            func()(realityfront.V4PublicLoopPulse,error){
                // Authenticated UDP uplink proves client TX, not the new
                // client's RAW RX socket and delivery route are installed.
                return realityfront.V4PublicLoopPulse{RxRecords:100},nil
            },func()error{promotions++;return nil},30*time.Millisecond)
        if err==nil||promotions!=0{
            t.Fatalf("server B promoted without exact client receiver proof: %v promotions=%d",err,promotions)
        }
    })
    t.Run("B_real_client_native_cold_Health_promotes_once",func(t *testing.T){
        pulses,promotions:=0,0
        err:=waitOriginalNativeServerClientM4Ready(context.Background(),
            func()(realityfront.V4PublicLoopPulse,error){
                pulses++
                if pulses<3{return realityfront.V4PublicLoopPulse{RxRecords:200},nil}
                return realityfront.V4PublicLoopPulse{AuthenticatedPeerControl:true},nil
            },func()error{promotions++;return nil},500*time.Millisecond)
        if err!=nil||pulses!=3||promotions!=1{
            t.Fatalf("authenticated client cold receipt did not promote server B once: err=%v pulses=%d promotions=%d",err,pulses,promotions)
        }
    })
    t.Run("terminal_client_fails_closed",func(t *testing.T){
        called:=false
        err:=waitOriginalNativeServerClientM4Ready(context.Background(),
            func()(realityfront.V4PublicLoopPulse,error){
                return realityfront.V4PublicLoopPulse{AuthenticatedPeerDead:true},nil
            },func()error{called=true;return nil},time.Second)
        if err==nil||called{t.Fatalf("dead client cannot steal A: err=%v",err)}
    })
}
