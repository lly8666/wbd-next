//go:build windows && wbd_v4_embedded_go
package realityfront

import (
 "context"
 "errors"
 "testing"

 "github.com/lly8666/wobuzhidao/internal/faketcp"
)

// Protected GameFec is the SAME original Go V4 TLV as the Linux owner.
// This unit prevents accepting unknown profile selectors before creating a
// native Rust group; it never claims Game M4/kernel/WinForms product PASS.
func TestM0WindowsGameFecProtectedExtensionBounds(t *testing.T){
 client:=make([]*faketcp.ClientAssociation,2)
 server:=make([]*faketcp.ServerAssociation,2)
 for _,invalid:=range []uint8{8,255}{
  _,err:=V4WindowsEstablishOriginalGameClientGroup(
   context.Background(),"",client,ClientAdmissionConfig{},invalid)
  if !errors.Is(err,ErrAdmissionUnsupported){
   t.Fatalf("untrusted Game2 FEC2 client profile=%d admitted: %v",invalid,err)
  }
  _,err=V4WindowsEstablishOriginalGameServerGroup(
   context.Background(),"",server,ServerAdmissionConfig{},nil,invalid)
  if !errors.Is(err,ErrAdmissionUnsupported){
   t.Fatalf("untrusted Game2 FEC2 server profile=%d admitted: %v",invalid,err)
  }
 }
 _,err:=V4WindowsEstablishOriginalGameClientGroup(
  context.Background(),"",client,ClientAdmissionConfig{},0,1)
 if !errors.Is(err,ErrAdmissionParams){
  t.Fatalf("multiple conflicting Game2 FEC profiles admitted: %v",err)
 }
 _,err=V4WindowsEstablishOriginalGameServerGroup(
  context.Background(),"",server,ServerAdmissionConfig{},nil,0,1)
 if !errors.Is(err,ErrAdmissionParams){
  t.Fatalf("multiple conflicting Game2 server FEC profiles admitted: %v",err)
 }
}

func TestM0WindowsGameOriginalV3CarrierPolicyMatchesLinuxFixedFour(t *testing.T){
 for _,lanes:=range []int{2,4}{
  policy,err:=FixedPolicyForClient(lanes,4)
  if err!=nil{t.Fatalf("Linux original V3 Game%d policy: %v",lanes,err)}
  // With missing actual associations we must reach the original
  // authenticated per-lane association check, not reject the legitimate
  // V3 fixed4 outer carrier before original TLS can even begin.
  cfg:=ClientAdmissionConfig{Policy:policy,DesiredLanes:uint8(lanes)}
  clients:=make([]*faketcp.ClientAssociation,lanes)
  _,err=V4WindowsEstablishOriginalGameClientGroup(
   context.Background(),"",clients,cfg,0)
  if !errors.Is(err,ErrAdmissionParams){
   t.Fatalf("original Game%d fixed4 V3 policy rejected before TLS: %v",lanes,err)
  }
 }
}

func TestM0WindowsGame4StaggeredNativeStageBoundedPartialNoInventedLane(t *testing.T){
 var rows [4]v4WindowsGameRawRecord
 rows[0].Lane=1
 rows[0].Length=51
 rows[0].PacketNumber=2
 rows[0].LogicalID=8
 rows[0].Wire[0]=0x10
 partial,err:=decodeOriginalGameStagedRecords(rows[:],1)
 if err!=nil||len(partial)!=1||partial[0].Lane!=1||len(partial[0].Wire)!=51 {
  t.Fatalf("delayed Game4 group forced all four copies: %v %#v",err,partial)
 }
 // The first due record gets independent private caller bytes.
 rows[0].Wire[0]=0xaa
 if partial[0].Wire[0]!=0x10{t.Fatal("borrowed unsafe native staged buffer")}
 empty,err:=decodeOriginalGameStagedRecords(rows[:],0)
 if err!=nil||len(empty)!=0{t.Fatal("no due record is not a real error")}
 if _,err=decodeOriginalGameStagedRecords(rows[:],5);err==nil{
  t.Fatal("native over-limit result was accepted")
 }
 rows[1]=rows[0]
 if _,err=decodeOriginalGameStagedRecords(rows[:],2);err==nil{
  t.Fatal("same lane counted twice in one real NPF batch")
 }
 rows[1].Lane=2
 records,err:=decodeOriginalGameStagedRecords(rows[:],2)
 if err!=nil||len(records)!=2||records[1].Lane!=2{
  t.Fatal("independently due lane must be accepted",err)
 }
}
