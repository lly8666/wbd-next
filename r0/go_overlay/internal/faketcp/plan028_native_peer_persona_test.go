package faketcp

import (
    "testing"
    "time"
)

// The only distinction is the existing *ordinary* original SYN option order.
// Identity/lease/owner still require protected original Go TLS, not this hint.
func TestPlan028OriginalSYNPersonaIndependentSessions(t *testing.T) {
    if err:=SetPublicV4AdvertisedMSS(1420);err!=nil{t.Fatal(err)}
    for _,tc:=range []struct{name string;persona PacketPersona}{
        {"linux-legacy",PacketPersonaLegacy},
        {"windows11",PacketPersonaWindows11},
    } {
        t.Run(tc.name,func(t *testing.T){
            syn:=Segment{
                SrcIP:[4]byte{192,0,2,10},DstIP:[4]byte{198,51,100,20},
                SrcPort:41031,DstPort:443,Seq:123,Window:4096,Flags:FlagSYN,
                MSS:1420,MSSSet:true,SACKPermitted:true,
                WindowScale:DefaultWindowScale,WindowScaleSet:true,
            }
            wire:=MarshalSegment(syn,1,tc.persona)
            got,err:=ParseIPv4TCP(wire)
            if err!=nil{t.Fatal(err)}
            if !got.OriginalSYNPersonaKnown || got.OriginalSYNPersona!=tc.persona{
                t.Fatalf("original SYN persona from actual options: known=%t value=%d expected=%d",
                    got.OriginalSYNPersonaKnown,got.OriginalSYNPersona,tc.persona)
            }
            assoc,err:=NewServerAssociation(got,567,time.Second,func(Segment)error{return nil})
            if err!=nil{t.Fatal(err)}
            profile:=assoc.PeerTCPProfile()
            if !profile.OriginalSYNPersonaKnown || profile.OriginalSYNPersona!=tc.persona{
                t.Fatalf("cold association lost immutable peer presentation: %+v",profile)
            }
        })
    }
}
func TestPlan028UnknownSYNOptionsDoNotInventPersona(t *testing.T) {
    syn:=Segment{SrcIP:[4]byte{192,0,2,10},DstIP:[4]byte{198,51,100,20},
        SrcPort:41032,DstPort:443,Seq:777,Flags:FlagSYN,Window:4096,
        MSS:1420,MSSSet:true,SACKPermitted:true,WindowScale:8,WindowScaleSet:true}
    raw:=MarshalSegment(syn,2,PacketPersonaLegacy)
    // Disturb only the option ORDER, leaving MSS/SACK/WS values intact:
    // unrecognized presentations cannot silently become a Windows owner.
    raw[51]=0 // change one final TCP NOP to EOL; preserve MSS/SACK/WS
    parsed,err:=ParseIPv4TCP(raw)
    if err!=nil{t.Fatal(err)}
    if parsed.OriginalSYNPersonaKnown{t.Fatal("unknown SYN option layout promoted a persona")}
    if parsed.MSS!=1420 || !parsed.WindowScaleSet{
        t.Fatal("pure cold option parser malformed existing recognized fields")
    }
}
