package realityfront

import (
    "errors"
    "testing"
)

func TestM0V4OriginalTLSGame2And4AuthenticatedColdSet(t *testing.T){
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
                if ce!=nil||se!=nil{t.Fatalf("real TLS lane%d client=%v server=%v",i,ce,se)}
                if i==1{epoch=c.Epoch}
                if c.Epoch!=epoch||s.Epoch!=epoch{t.Fatalf("lane%d epoch",i)}
                clients=append(clients,c)
                servers=append(servers,s)
            }
            // A shuffled caller's slice does not change the 1..N lane-key
            // mapping passed into native GameAdapter. All lane keys/PN
            // allocators originate from independent original TLS exporters.
            clients[0],clients[n-1]=clients[n-1],clients[0]
            servers[0],servers[n-1]=servers[n-1],servers[0]
            send,err:=v4OriginalGameServerColdSet(servers...)
            if err!=nil{t.Fatalf("server cold set: %v",err)}
            recv,err:=v4OriginalGameClientColdSet(clients...)
            if err!=nil{t.Fatalf("client cold set: %v",err)}
            if len(send)!=n||len(recv)!=n{t.Fatal("not exact 2/4")}
            for i:=0;i<n;i++{
                if send[i].laneID!=uint8(i+1)||recv[i].laneID!=uint8(i+1)||
                    send[i].keys!=recv[i].keys||send[i].epoch!=epoch||
                    send[i].features!=v4RequiredFeatures|v4FeatureFEC2{
                    t.Fatalf("TLS lane%d cold identity mismatch",i+1)
                }
                for j:=0;j<i;j++{
                    if send[i].incarnation==send[j].incarnation||
                       send[i].keys.C2S==send[j].keys.C2S||
                       send[i].keys.S2C==send[j].keys.S2C{
                        t.Fatalf("lane%d reused exporter key",i+1)
                    }
                }
            }
            if _,e:=v4OriginalGameClientColdSet(clients[0]);!errors.Is(e,ErrAdmissionParams){
                t.Fatalf("single lane became a Game set: %v",e)
            }
            duplicates:=append([]*V4ClientSession(nil),clients...)
            duplicates[n-1]=duplicates[0]
            if _,e:=v4OriginalGameClientColdSet(duplicates...);!errors.Is(e,ErrAdmissionParams){
                t.Fatalf("duplicate TLS lane admitted: %v",e)
            }
            if _,e:=v4OriginalGameServerColdSet(servers[:n-1]...);e==nil{
                t.Fatal("incomplete Game server set admitted")
            }
            bad:=clients[0]
            originalPolicy:=bad.Negotiated.Policy
            bad.Negotiated.Policy.Transport=TransportNormal
            if _,e:=v4OriginalGameClientColdSet(clients...);!errors.Is(e,ErrAdmissionParams){
                t.Fatalf("mutable post-TLS Game policy admitted: %v",e)
            }
            bad.Negotiated.Policy=originalPolicy
            originalKeys:=bad.Negotiated.Keys
            bad.Negotiated.Keys.C2S.AEADKey[0]^=0x80
            if _,e:=v4OriginalGameClientColdSet(clients...);!errors.Is(e,ErrAdmissionParams){
                t.Fatalf("mutable post-TLS C2S key admitted: %v",e)
            }
            bad.Negotiated.Keys=originalKeys
            // Even a well-formed copied cold snapshot with the same epoch
            // cannot insert feature3 into a feature7 Game group.
            forged:=append([]V4ColdSessionSnapshot(nil),recv...)
            forged[1].features=v4RequiredFeatures
            policies:=make([]AdmissionPolicy,n)
            for i:=range policies{policies[i]=policy}
            if _,e:=v4CheckAuthenticatedGameLanes(forged,policies,false);e==nil{
                t.Fatal("cross-feature private cold group admitted")
            }
            forged=append([]V4ColdSessionSnapshot(nil),recv...)
            forged[1].principal="another-user"
            if _,e:=v4CheckAuthenticatedGameLanes(forged,policies,false);e==nil{
                t.Fatal("cross-principal private cold group admitted")
            }
            for i:=1;i<=n;i++{
                if e:=store.ReleaseLane("game-user",tunnel,uint8(i),epoch);e!=nil{
                    t.Fatalf("release lane%d: %v",i,e)
                }
            }
            t.Logf("M0_ORIGINAL_GO_TLS_GAME_AUTHENTICATED_COLD_SET_PASS lanes=%d independent_exporter_keys=1 original_TLS=1 mixed_features_denied=1 post_TLS_mutation_denied=1 INDEPENDENT_M4_RAW_KERNEL_FIRST_APP_NOT_RUN=1 GAME_PRODUCTION_OFF=1",n)
        })
    }
}
