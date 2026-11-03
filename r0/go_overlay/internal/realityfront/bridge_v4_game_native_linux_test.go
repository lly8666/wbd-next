//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product
package realityfront
import ("errors";"fmt";"testing")
func TestM0Plan019NativeGameGroupRejectsMissingCommittedOriginalTLS(t *testing.T){
    var zero *V4LinuxGameVerifiedGroup
    if _,err:=zero.joinAuthenticatedOriginalRust(&v4EmbeddedNativeBridge{},&v4EmbeddedNativeBridge{});!errors.Is(err,ErrAdmissionParams){
        t.Fatalf("nil verified group got %v",err)
    }
    // No Go caller can create a native shared Game AEAD group out of
    // arbitrary references that merely have fabricated Go handle fields.
    g:=&V4LinuxGameVerifiedGroup{}
    if _,err:=g.joinAuthenticatedOriginalRust(&v4EmbeddedNativeBridge{
        handle:1,committed:true,protectedLane:1,
    },&v4EmbeddedNativeBridge{
        handle:2,committed:true,protectedLane:2,
    });!errors.Is(err,ErrAdmissionUnsupported){
        t.Fatalf("unverified cold became Game shared owner: %v",err)
    }
    t.Log("M0_PLAN019_NATIVE_GAME_SHARED_ORIGINAL_TLS_MISSING_AUTH_DENIED native_driver_NOT_RUN=1")
}

func TestPLAN028AuthenticatedGameCohortSeparatesAccountsAndDevices(t *testing.T){
    // Two separate original credential-protected TLS Game2 cohorts.
    // Never join same source IP/port/arrival index as identity.
    store,err:=NewV4EpochStore(8)
    if err!=nil{t.Fatal(err)}
    policy:=v4TestPolicy(2,CipherChaCha)
    var keys [2]V4LinuxGameCohortID
    for group,principal:=range []string{"alice","bob"}{
        tunnel:=[]byte(fmt.Sprintf("cohort%010d",group)) // 16 exact bytes
        var epoch [16]byte
        for lane:=1;lane<=2;lane++{
            client,server,ce,se:=v4PairFeatureProbe(t,store,principal,
                tunnel,uint8(lane),policy,epoch,true,true)
            if ce!=nil||se!=nil{t.Fatalf("real TLS group%d lane%d: %v %v",group,lane,ce,se)}
            if lane==1{epoch=client.Epoch}
            authenticated:=&V4LinuxGameAuthenticatedLane{
                session:server,bridge:&v4EmbeddedNativeBridge{},
            }
            key,id,e:=authenticated.Cohort()
            if e!=nil||id!=uint8(lane)||key.Principal!=principal||key.Lanes!=2{
                t.Fatalf("authenticated Game cohort group%d lane%d: key=%+v id=%d err=%v",
                    group,lane,key,id,e)
            }
            if lane==1{keys[group]=key}else if keys[group]!=key{
                t.Fatalf("one original TLS Game group split across lanes")
            }
        }
    }
    if keys[0]==keys[1]{
        t.Fatal("different credential/installation accepted into same group")
    }
    if _,_,err:=(*V4LinuxGameAuthenticatedLane)(nil).Cohort();err==nil{
        t.Fatal("nil pre-TLS Game lane was accepted as authenticated")
    }
}
