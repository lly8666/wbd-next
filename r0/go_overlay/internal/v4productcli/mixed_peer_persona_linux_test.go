//go:build linux && cgo && wbd_v4_embedded_go && wbd_v4_fec2_product

package v4productcli

import (
 "testing"
 "time"

 "github.com/lly8666/wobuzhidao/internal/faketcp"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
)

// Real original SYN bytes, not a mode selected from caller-controlled
// username/IP. The shared Go/TLS server consults this only after actual
// authenticated lane admission, for one Rust M4 peer receiver's persona.
func TestPLAN028MixedServerPerOriginalAssociationSYNPersona(t *testing.T){
 if err:=faketcp.SetPublicV4AdvertisedMSS(1420);err!=nil{t.Fatal(err)}
 assoc:=func(persona faketcp.PacketPersona,port uint16)*faketcp.ServerAssociation{
  syn:=faketcp.Segment{
   SrcIP:[4]byte{192,0,2,10},DstIP:[4]byte{198,51,100,20},
   SrcPort:port,DstPort:443,Seq:123,Window:4096,Flags:faketcp.FlagSYN,
   MSS:1420,MSSSet:true,SACKPermitted:true,
   WindowScale:faketcp.DefaultWindowScale,WindowScaleSet:true,
  }
  wire:=faketcp.MarshalSegment(syn,1,persona)
  parsed,err:=faketcp.ParseIPv4TCP(wire)
  if err!=nil{t.Fatal(err)}
  if !parsed.OriginalSYNPersonaKnown||parsed.OriginalSYNPersona!=persona{
   t.Fatalf("actual original SYN option order not recognized persona=%d: %+v",persona,parsed)
  }
  got,err:=faketcp.NewServerAssociation(parsed,567,time.Second,func(faketcp.Segment)error{return nil})
  if err!=nil{t.Fatal(err)}
  return got
 }
 win:=assoc(faketcp.PacketPersonaWindows11,41031)
 lin:=assoc(faketcp.PacketPersonaLegacy,43031)
 for _,tc:=range []struct{
  name string;peer *faketcp.ServerAssociation
  fallback,want realityfront.V4PublicNativePeerPersona
 }{
  {"Windows original vs fallback Linux",win,realityfront.V4PeerLegacy,realityfront.V4PeerWindows11},
  {"Linux original vs fallback Windows",lin,realityfront.V4PeerWindows11,realityfront.V4PeerLegacy},
  {"Windows independent of process-wide Windows",win,realityfront.V4PeerWindows11,realityfront.V4PeerWindows11},
  {"Linux independent of process-wide Linux",lin,realityfront.V4PeerLegacy,realityfront.V4PeerLegacy},
 }{
  actual,known:=originalV4ColdAssocPeerPersona(tc.peer,tc.fallback)
  if !known||actual!=tc.want{t.Fatalf("%s: actual=%d expected=%d known=%t",tc.name,actual,tc.want,known)}
 }
 for _,f:=range []realityfront.V4PublicNativePeerPersona{
  realityfront.V4PeerWindows11,realityfront.V4PeerLegacy,
 }{
  actual,known:=originalV4ColdAssocPeerPersona(nil,f)
  if known||actual!=f{t.Fatal("unknown association fabricated original peer persona")}
 }
 t.Log("PLAN028_ORIGINAL_MIXED_NORMAL_AND_GAME_PER_ASSOC_SYN_PERSONA_UNIT_PASS")
}
