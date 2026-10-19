//go:build linux && cgo && wbd_v4_embedded_go
package realityfront
import "testing"

// Typical real Go TLS Normal/OFF user-config lifecycle. The only actual
// native FEC state is OFF; fixed/auto are rejected until qualified.
func TestR0V4EmbeddedNormalOffProductRevisionReadback(t *testing.T){
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        store,e:=NewV4EpochStore(1);if e!=nil{t.Fatal(e)}
        b:=&v4EmbeddedNativeBridge{}
        client,server,ce,se:=v4PairWithPrivateBridgeCipher(t,b,store,cipher)
        if ce!=nil||se!=nil||client==nil||server==nil||!b.committed{
            t.Fatalf("verified Go TLS cipher=%d: %v %v",cipher,ce,se)
        }
        epoch:=server.Epoch
        cfg:=FecV2Config{Client:b.authenticatedPrincipal,
            Direction:FecV2S2C,Transport:FecV2Normal,Mode:FecV2Off,
            ConfigRevision:1}
        pending,ack,e:=b.stageOriginalNormalOff(cfg,FecV2State{},epoch)
        if e!=nil||!pending.Initialized||pending.RequestedRevision!=1||
           pending.AppliedRevision!=0||ack.Applied||ack.Rejected{
            t.Fatalf("OFF must first be pending %+v %+v %v",pending,ack,e)
        }
        applied,ok,e:=b.readbackOriginalNormalOff(pending,epoch)
        if e!=nil||!ok.Applied||!ok.Off||!applied.AppliedOff||
           applied.AppliedRevision!=1{t.Fatalf("actual Rust OFF readback missing %+v %+v %v",applied,ok,e)}
        denied:=cfg;denied.ConfigRevision=2;denied.Mode=FecV2Fixed
        same,rejected,e:=b.stageOriginalNormalOff(denied,applied,epoch)
        if e==nil||!rejected.Rejected||same!=applied{
            t.Fatalf("fixed not supported must reject %+v %+v %v",same,rejected,e)
        }
        denied.Mode=FecV2Auto
        denied.AutoPolicy=FecV2Conservative // legal automatic config, must reach explicit native refusal
        _,rejected,e=b.stageOriginalNormalOff(denied,applied,epoch)
        if e==nil||!rejected.Rejected{t.Fatal("auto not supported must reject")}
        wrong:=cfg;wrong.ConfigRevision=2;wrong.Client="wrong-principal"
        if _,_,e=b.stageOriginalNormalOff(wrong,applied,epoch);e==nil{
            t.Fatal("unverified principal accepted")
        }
        wrongEpoch:=epoch;wrongEpoch[0]^=1
        if _,_,e=b.stageOriginalNormalOff(cfg,applied,wrongEpoch);e==nil{
            t.Fatal("wrong authenticated epoch accepted")
        }
        cfg.ConfigRevision=2
        next,ack,e:=b.stageOriginalNormalOff(cfg,applied,epoch)
        if e!=nil||next.RequestedRevision!=2||next.AppliedRevision!=1||ack.Applied{
            t.Fatalf("second off revision skipped pending %+v %+v %v",next,ack,e)
        }
        applied,ok,e=b.readbackOriginalNormalOff(next,epoch)
        if e!=nil||!ok.Applied||applied.AppliedRevision!=2{
            t.Fatalf("second actual Rust OFF readback %+v %+v %v",applied,ok,e)
        }
        if _,_,e=b.stageOriginalNormalOff(cfg,applied,epoch);e==nil{
            t.Fatal("stale config revision accepted")
        }
        stopped,e:=b.StopAndReleaseOriginalOwner()
        if e!=nil||!stopped.OwnerAndDriversDrained||!stopped.GenerationReleased{
            t.Fatalf("Stop not completed %+v %v",stopped,e)
        }
        if _,_,e=b.readbackOriginalNormalOff(applied,epoch);e==nil{
            t.Fatal("stopped owner gave positive ACK")
        }
        if e:=store.ReleaseLane("protected-owner",[]byte("0123456789abcdef"),1,epoch);e!=nil{t.Fatal(e)}
        t.Logf("M0_ORIGINAL_GO_NORMAL_OFF_REQUEST_PENDING_APPLIED_REJECTED_PASS cipher=%d real_revision=2 wrong_client_denied=1 wrong_epoch_denied=1 fixed_auto_rejected=1 stop=1",cipher)
    }
}
