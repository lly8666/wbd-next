//go:build linux && cgo && wbd_v4_embedded_go

package realityfront

import (
    "errors"
    "testing"
)

func TestM0Plan019RealTLSGroup2And4ImmutableOwnerBoundary(t *testing.T){
    for _,n:=range []int{2,4}{
        t.Run(string(rune('0'+n)),func(t *testing.T){
            store,err:=NewV4EpochStore(4)
            if err!=nil{t.Fatal(err)}
            tunnel:=[]byte("game-TLS-0123456")
            policy:=v4TestPolicy(uint8(n),CipherChaCha)
            clients:=make([]*V4ClientSession,0,n)
            servers:=make([]*V4ServerSession,0,n)
            var epoch [16]byte
            for i:=1;i<=n;i++{
                c,s,ce,se:=v4PairFeatureProbe(t,store,"game-user",tunnel,
                    uint8(i),policy,epoch,true,true)
                if ce!=nil||se!=nil{t.Fatalf("real TLS lane%d: %v %v",i,ce,se)}
                if i==1{epoch=c.Epoch}
                clients=append(clients,c);servers=append(servers,s)
            }
            cg,err:=V4LinuxGameClientVerifiedGroup(clients...)
            if err!=nil{t.Fatal(err)}
            sg,err:=V4LinuxGameServerVerifiedGroup(servers...)
            if err!=nil{t.Fatal(err)}
            ci,err:=cg.OriginalTLSIdentity()
            if err!=nil{t.Fatal(err)}
            si,err:=sg.OriginalTLSIdentity()
            if err!=nil{t.Fatal(err)}
            if ci!=si||int(ci.Lanes)!=n||ci.Epoch!=epoch||
               ci.Features!=v4RequiredFeatures|v4FeatureFEC2{
                t.Fatal("original independent original-Go TLS group identity")
            }
            callbackCount:=0
            err=cg.withPrivateOriginalTLS(func(ordered []V4ColdSessionSnapshot)error{
                callbackCount++
                if len(ordered)!=n{return ErrAdmissionParams}
                for i,cold:=range ordered{
                    if cold.laneID!=uint8(i+1)||cold.epoch!=epoch{
                        return ErrAdmissionParams
                    }
                }
                return nil
            })
            if err!=nil||callbackCount!=1{t.Fatalf("private Go grant %v %d",err,callbackCount)}
            // A mutation to a formerly verified TLS session cannot create
            // a new live grouped grant or change any frozen existing group.
            original:=clients[0].Negotiated.Keys
            clients[0].Negotiated.Keys.C2S.AEADKey[0]^=0x40
            if _,e:=V4LinuxGameClientVerifiedGroup(clients...);!errors.Is(e,ErrAdmissionParams){
                t.Fatalf("mutated original TLS key admitted %v",e)
            }
            clients[0].Negotiated.Keys=original
            duplicate:=append([]*V4ClientSession(nil),clients...)
            duplicate[n-1]=duplicate[0]
            if _,e:=V4LinuxGameClientVerifiedGroup(duplicate...);e==nil{
                t.Fatal("duplicate independent lane admitted")
            }
            if _,e:=V4LinuxGameClientVerifiedGroup(clients[:n-1]...);e==nil{
                t.Fatal("partial original TLS group admitted")
            }
            if err:=cg.revoke();err!=nil{t.Fatal(err)}
            if err:=cg.revoke();err!=nil{t.Fatal(err)}
            if _,err:=cg.OriginalTLSIdentity();!errors.Is(err,ErrAdmissionUnsupported){
                t.Fatalf("stale after revoked group %v",err)
            }
            if err:=cg.withPrivateOriginalTLS(func(_ []V4ColdSessionSnapshot)error{
                t.Fatal("stale native callback fired");return nil
            });!errors.Is(err,ErrAdmissionUnsupported){t.Fatalf("stale callback %v",err)}
            if err:=sg.revoke();err!=nil{t.Fatal(err)}
            for i:=1;i<=n;i++{
                if err:=store.ReleaseLane("game-user",tunnel,uint8(i),epoch);err!=nil{
                    t.Fatalf("original Go lane release %d: %v",i,err)
                }
            }
            t.Logf("M0_PLAN019_REAL_ORIGINAL_GO_TLS_PUBLIC_GAME_GROUP_BOUNDARY_PASS lanes=%d frozen_original_credentials=1 exact_group_epoch=1 duplicate_tamper_partial_denied=1 native_group_NOT_WIRED=1",n)
        })
    }
}
