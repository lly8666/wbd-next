//go:build windows
package main
import "testing"
func TestPlan029ServerDomainValidationIsNotTLSNameOrNetworkIO(t *testing.T){
 for _,input:=range []string{"node.example.com","NODE.Example.COM.","xn--bcher-kva.example"}{
  got,e:=m0CanonicalWindowsServerHost(input)
  if e!=nil||got==""{t.Fatalf("valid name %s: %v",input,e)}
 }
 for _,input:=range []string{"::1","", "127.0.0.999","single-label","a..b","-bad.example","a/b.example"}{
  if _,e:=m0CanonicalWindowsServerHost(input);e==nil{t.Fatalf("bad domain allowed: %q",input)}
 }
}
