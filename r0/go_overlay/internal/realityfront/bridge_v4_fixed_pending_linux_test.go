//go:build linux && cgo && wbd_v4_embedded_go
package realityfront

import "testing"

// Three ORIGINAL Go credential-verified TLS suites and genuine Rust
// protected owner, not a cold248 fixture. No actual FEC data means zero
// positive applied revisions. This test is about fail-closed control wiring.
func TestR0V4EmbeddedFixedPendingRealGoTLSNoPrematureApplied(t *testing.T){
    for _,cipher:=range []uint8{CipherChaCha,CipherAES128,CipherAES256}{
        t.Run(string(rune('0'+cipher)),func(t *testing.T){
            store,e:=NewV4EpochStore(2);if e!=nil{t.Fatal(e)}
            normal:=&v4EmbeddedNativeBridge{}
            _,normalServer,ce,se:=v4PairWithPrivateBridgeCipher(
                t,normal,store,cipher)
            if ce!=nil||se!=nil||normalServer==nil||!normal.committed{
                t.Fatalf("normal TLS owner: %v %v",ce,se)
            }
            cfg:=FecV2Config{
                Client:"protected-owner",Direction:FecV2S2C,
                Transport:FecV2Normal,Mode:FecV2Fixed,
                Profile:FecV2High,ConfigRevision:1,
            }
            if _,ack,e:=normal.stageOriginalFixedPending(
                cfg,FecV2State{},normalServer.Epoch,
            );e==nil||!ack.Rejected{
                t.Fatal("normal authenticated feature3 was falsely granted FEC2")
            }
            if e:=normal.stopRelease();e!=nil{t.Fatal(e)}
            if e:=store.ReleaseLane("protected-owner",
                []byte("0123456789abcdef"),1,normalServer.Epoch);e!=nil{
                t.Fatal(e)
            }

            fixed:=&v4EmbeddedNativeBridge{}
            client,server,ce,se:=v4PairWithPrivateBridgeCipher(
                t,fixed,store,cipher,true)
            if ce!=nil||se!=nil||client==nil||server==nil||!fixed.committed||
                fixed.protectedFeatures!=(v4RequiredFeatures|v4FeatureFEC2){
                t.Fatalf("bit2 protected Go TLS original owner: %v %v",ce,se)
            }
            wrong:=server.Epoch;wrong[0]^=0x41
            if _,ack,e:=fixed.stageOriginalFixedPending(
                cfg,FecV2State{},wrong,
            );e==nil||!ack.Rejected{
                t.Fatal("foreign epoch claimed original protected Fixed owner")
            }
            pending,ack,e:=fixed.stageOriginalFixedPending(
                cfg,FecV2State{},server.Epoch)
            if e!=nil||ack.Applied||ack.Rejected||pending.RequestedRevision!=1||
                pending.AppliedRevision!=0||pending.DesiredOff||
                pending.Desired!=FecV2High{
                t.Fatalf("real TLS pending requested only: %+v %+v err=%v",
                    pending,ack,e)
            }
            read,ack,e:=fixed.readbackOriginalFixedPending(pending,server.Epoch)
            if e!=nil||ack.Applied||ack.Rejected||read.AppliedRevision!=0{
                t.Fatalf("pending was falsely treated as FEC product APPLIED: %+v %+v %v",read,ack,e)
            }
            if _,ack,e:=fixed.stageOriginalFixedPending(
                cfg,pending,server.Epoch,
            );e==nil||!ack.Rejected{
                t.Fatal("duplicate config revision accepted")
            }
            cfg2:=cfg;cfg2.ConfigRevision=2;cfg2.Profile=FecV2Strong
            second,ack,e:=fixed.stageOriginalFixedPending(cfg2,pending,server.Epoch)
            if e!=nil||ack.Applied||ack.Rejected||second.RequestedRevision!=2||
                second.Desired!=FecV2Strong||second.AppliedRevision!=0{
                t.Fatalf("Fixed next revision incorrectly applied: %+v %+v %v",
                    second,ack,e)
            }
            if _,_,e:=fixed.readbackOriginalFixedPending(pending,server.Epoch);e==nil{
                t.Fatal("stale requested revision readback conflated newer pending")
            }
            if _,ack,e:=fixed.readbackOriginalFixedPending(second,server.Epoch);
                e!=nil||ack.Applied{
                t.Fatalf("second fixed request falsely applied: %+v %v",ack,e)
            }
            offCfg:=cfg;offCfg.Mode=FecV2Off;offCfg.ConfigRevision=3
            offPending,offAck,e:=fixed.stageOriginalNormalOff(
                offCfg,second,server.Epoch)
            if e!=nil||offAck.Applied||offPending.RequestedRevision!=3{
                t.Fatalf("original Rust OFF did not cancel Fixed pending: %+v %v",offAck,e)
            }
            if _,_,e:=fixed.readbackOriginalFixedPending(second,server.Epoch);e==nil{
                t.Fatal("OFF retained stale Fixed policy")
            }
            _,offAck,e=fixed.readbackOriginalNormalOff(offPending,server.Epoch)
            if e!=nil||!offAck.Applied||!offAck.Off{
                t.Fatalf("actual quiescent OFF not applied: %+v %v",offAck,e)
            }
            if e:=fixed.stopRelease();e!=nil{t.Fatal(e)}
            if _,_,e:=fixed.readbackOriginalFixedPending(second,server.Epoch);e==nil{
                t.Fatal("retired generation retained a Fixed pending readback")
            }
            if e:=store.ReleaseLane("protected-owner",
                []byte("0123456789abcdef"),1,server.Epoch);e!=nil{
                t.Fatal(e)
            }
            t.Logf("M0_FIXED_ORIGINAL_TLS_PENDING_ONLY_PASS cipher=%d revisions=1,2 applied=0 foreign=deny original_off3=applied stop=deny",cipher)
        })
    }
}
