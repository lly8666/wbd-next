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
