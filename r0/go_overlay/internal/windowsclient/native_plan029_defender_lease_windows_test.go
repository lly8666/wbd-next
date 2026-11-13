//go:build windows

package windowsclient

import (
 "context"
 "crypto/rand"
 "errors"
 "net/netip"
 "os"
 "path/filepath"
 "testing"
)
type p029DefenderFake struct{
 rules map[string]n4Plan029DefenderKey
 adds,removes int
 failAfterAdd bool
 tamper bool
}
func(b *p029DefenderFake)Lookup(_ context.Context,k n4Plan029DefenderKey)(
 bool,bool,error){
 if b.rules==nil{return false,false,nil}
 found,ok:=b.rules[k.Name]
 return ok,ok&&found==k&&!b.tamper,nil
}
func(b *p029DefenderFake)CreateIfAbsent(ctx context.Context,k n4Plan029DefenderKey)error{
 if e:=ctx.Err();e!=nil{return e}
 if b.rules==nil{b.rules=make(map[string]n4Plan029DefenderKey)}
 if _,yes:=b.rules[k.Name];yes{return ErrN4ForeignRoute}
 b.rules[k.Name]=k;b.adds++
 if b.failAfterAdd{return errors.New("injected power loss AFTER OS Add BEFORE owned receipt")}
 return nil
}
func(b *p029DefenderFake)RemoveOwned(ctx context.Context,k n4Plan029DefenderKey)error{
 if e:=ctx.Err();e!=nil{return e}
 found,ok:=b.rules[k.Name]
 if !ok||b.tamper||found!=k{return ErrN4ForeignRoute}
 delete(b.rules,k.Name);b.removes++
 return nil
}
func p029DefenderFixture(t *testing.T)(N4UnifiedIdentity,n4Plan029DefenderKey,string){
 t.Helper()
 id:=n4TestConcreteNativeIdentity()
 if !id.valid(){t.Fatal("fixture must represent one actual native identity")}
 lease:=netip.MustParseAddr("10.234.12.34")
 synthetic:=netip.MustParseAddr("198.19.87.99")
 k,e:=n4Plan029DefenderKeyFor(id,lease,synthetic,45321)
 if e!=nil{t.Fatal(e)}
 return id,k,filepath.Join(t.TempDir(),"n4-state.defender")
}
func TestPlan029DefenderExactlyOwnedSinglePortRuleAndCASStop(t *testing.T){
 ctx:=context.Background()
 id,k,path:=p029DefenderFixture(t)
 b:=&p029DefenderFake{}
 if e:=n4Plan029DefenderInstall(ctx,path,id,k,b);e!=nil{t.Fatal(e)}
 if b.adds!=1||b.removes!=0{t.Fatalf("non exact Add: %+v",b)}
 rec,e:=n4Plan029ReadDefender(path,id,k)
 if e!=nil||rec.Phase!="owned"{t.Fatalf("not durable owned receipt: %+v %v",rec,e)}
 if e=n4Plan029DefenderRecover(ctx,path,id,k,b);e!=nil{t.Fatal(e)}
 if b.removes!=1||len(b.rules)!=0{t.Fatalf("not exactly one CAS delete: %+v",b)}
 if _,e=os.Stat(path);!errors.Is(e,os.ErrNotExist){
  t.Fatalf("Stop retained stale sidecar: %v",e)
 }
 if e=n4Plan029DefenderRecover(ctx,path,id,k,b);e!=nil{
  t.Fatalf("idempotent exact absence Stop failed: %v",e)
 }
 if b.removes!=1{t.Fatal("duplicate Stop attempted broad delete")}
}
func TestPlan029DefenderUnconfirmedAddIsNeverGuessedOwned(t *testing.T){
 ctx:=context.Background()
 id,k,path:=p029DefenderFixture(t)
 b:=&p029DefenderFake{failAfterAdd:true}
 if e:=n4Plan029DefenderInstall(ctx,path,id,k,b);e==nil{
  t.Fatal("Add-after-OS-before-WAL failure must fail closed")
 }
 rec,e:=n4Plan029ReadDefender(path,id,k)
 if e!=nil||rec.Phase!="intent"{t.Fatal("lost pre-write durable intent",e)}
 b.failAfterAdd=false
 if e:=n4Plan029DefenderRecover(ctx,path,id,k,b);
  !errors.Is(e,ErrN4RouteAmbiguous){
  t.Fatalf("unconfirmed present rule falsely cleaned: %v",e)
 }
 if b.removes!=0{t.Fatal("unconfirmed rule deleted")}
 if _,e=os.Stat(path);e!=nil{t.Fatal("unconfirmed receipt was unlinked",e)}
 // An operator/OS may prove it is absent. At that point ONLY the intent
 // sidecar can safely be discarded; no extra native firewall deletion.
 delete(b.rules,k.Name)
 if e=n4Plan029DefenderRecover(ctx,path,id,k,b);e!=nil{t.Fatal(e)}
 if b.removes!=0{t.Fatal("recovery synthesized a deletion")}
}
func TestPlan029DefenderForeignExactNameAndEditedPolicyNeverDeleted(t *testing.T){
 ctx:=context.Background()
 id,k,path:=p029DefenderFixture(t)
 b:=&p029DefenderFake{rules:map[string]n4Plan029DefenderKey{k.Name:k}}
 if e:=n4Plan029DefenderInstall(ctx,path,id,k,b);
  !errors.Is(e,ErrN4ForeignRoute){t.Fatal("foreign existing rule admitted",e)}
 if b.adds!=0||b.removes!=0{t.Fatal("foreign admission mutated Defender")}
 delete(b.rules,k.Name)
 if e:=n4Plan029DefenderInstall(ctx,path,id,k,b);e!=nil{t.Fatal(e)}
 b.tamper=true
 if e:=n4Plan029DefenderRecover(ctx,path,id,k,b);
  !errors.Is(e,ErrN4ForeignRoute){t.Fatal("edited rule deleted by owner",e)}
 if b.removes!=0{t.Fatal("foreign rule incorrectly deleted")}
 if _,e:=os.Stat(path);e!=nil{t.Fatal("foreign rule must retain WAL",e)}
}
func TestPlan029DefenderCorruptWALAndWrongGenerationCannotStop(t *testing.T){
 ctx:=context.Background()
 id,k,path:=p029DefenderFixture(t)
 b:=&p029DefenderFake{}
 if e:=n4Plan029DefenderInstall(ctx,path,id,k,b);e!=nil{t.Fatal(e)}
 other:=id;other.Generation[0]^=1
 if e:=n4Plan029DefenderRecover(ctx,path,other,k,b);
  !errors.Is(e,ErrN4JournalConflict){
  t.Fatal("foreign generation is not an own receipt",e)
 }
 if b.removes!=0{t.Fatal("foreign generation caused delete")}
 if e:=os.WriteFile(path,[]byte("{\"data\":{},\"sha256\":\"bad\"}"),0600);e!=nil{
  t.Fatal(e)
 }
 if e:=n4Plan029DefenderRecover(ctx,path,id,k,b);
  !errors.Is(e,ErrN4JournalConflict){t.Fatal("corrupt WAL admitted",e)}
 if b.removes!=0{t.Fatal("corrupt WAL caused delete")}
}
func TestPlan029DefenderExactSyntheticLeasePortOnly(t *testing.T){
 id,k,_:=p029DefenderFixture(t)
 if k.Port!=45321||k.Lease4.String()!="10.234.12.34"||
  k.Remote4.String()!="198.19.87.99"{t.Fatal(k)}
 invalid:=[]netip.Addr{
  netip.MustParseAddr("198.18.0.2"),
  netip.MustParseAddr("198.19.2.0"),
  netip.MustParseAddr("198.19.2.255"),
  netip.MustParseAddr("127.0.0.1"),
  netip.IPv4Unspecified(),
 }
 for _,addr:=range invalid{
  if _,e:=n4Plan029DefenderKeyFor(id,k.Lease4,addr,45321);e==nil{
   t.Fatal("foreign/unscoped remote source",addr)
  }
 }
 if _,e:=n4Plan029DefenderKeyFor(id,k.Lease4,k.Remote4,0);e==nil{
  t.Fatal("wildcard port")
 }
 other:=id;other.Generation[0]^=1
 k2,e:=n4Plan029DefenderKeyFor(other,k.Lease4,k.Remote4,45321)
 if e!=nil||k2.Name==k.Name||k2.Description==k.Description{
  t.Fatal("exact firewall owner generation not in private rule identity",e)
 }
}

func TestPlan029DefenderReadbackExactSingleHostOnly(t *testing.T){
 host:="10.234.12.34"
 for _,s:=range []string{host,host+"/255.255.255.255"}{
  if !n4Plan029ExactIPv4HostScope(s,host){t.Fatalf("exact host rejected %s",s)}
 }
 for _,s:=range []string{"10.234.12.35","10.234.12.34/24",
  "10.234.12.34/255.255.255.0","10.234.12.34/255.255.255.254",
  "10.234.12.34,10.234.12.35","10.234.12.34;10.234.12.35",
  "*","Any","10.234.12.34/32",""," 10.234.12.34"}{
  if n4Plan029ExactIPv4HostScope(s,host){t.Fatalf("broadened rule %q",s)}
 }
}

// The only native Defender COM mutation in this workflow is opt-in and
// source-locked on a disposable Windows CI runner. It opens no reachable
// socket, claims no product Applied/Ready, and must prove the exact
// one-lease-IP/one-remote-IP/one-port allow has been removed BEFORE PASS.
func TestPlan029DefenderNativeCOMOneRealRuleOwnedCAS(t *testing.T){
 if os.Getenv("GITHUB_ACTIONS")!="true"||
  os.Getenv("WBD_PLAN029_REAL_DEFENDER_TEST")!="1"{
  t.Skip("native Defender mutation is only authorized on ephemeral CI")
 }
 id,k,path:=p029DefenderFixture(t)
 if _,e:=rand.Read(id.Generation[:]);e!=nil{t.Fatal(e)}
 k,e:=n4Plan029DefenderKeyFor(id,k.Lease4,k.Remote4,k.Port)
 if e!=nil{t.Fatal(e)}
 ctx,cancel:=context.WithTimeout(context.Background(),30_000_000_000)
 defer cancel()
 backend:=n4Plan029DefenderCOM{}
 present,_,e:=backend.Lookup(ctx,k)
 if e!=nil||present{t.Fatalf("native Defender preflight unavailable/foreign: %v present=%v",e,present)}
 // Cleanup is a second source-locked check, but no unconfirmed OS rule
 // can be guessed owned; a failed Create leaves evidence for recovery.
 defer func(){
  cleanup,stop:=context.WithTimeout(context.Background(),15_000_000_000)
  defer stop()
  if e:=n4Plan029DefenderRecover(cleanup,path,id,k,backend);e!=nil{
   t.Errorf("exact owned Defender cleanup failed (WAL retained): %v",e)
  }
 }()
 if e=n4Plan029DefenderInstall(ctx,path,id,k,backend);e!=nil{
  t.Fatalf("native exact IN/TCP firewall Add/readback failed: %v",e)
 }
 rec,e:=n4Plan029ReadDefender(path,id,k)
 if e!=nil||rec.Phase!="owned"{
  t.Fatalf("real COM rule missing durable owner: %+v %v",rec,e)
 }
 present,exact,e:=backend.Lookup(ctx,k)
 if e!=nil||!present||!exact{
  t.Fatalf("real Windows Defender exact rule mismatch: present=%v exact=%v err=%v",present,exact,e)
 }
 if e=n4Plan029DefenderRecover(ctx,path,id,k,backend);e!=nil{
  t.Fatalf("native exact firewall CAS removal failed: %v",e)
 }
 present,_,e=backend.Lookup(ctx,k)
 if e!=nil||present{
  t.Fatalf("native Defender leftover after Stop: %v present=%v",e,present)
 }
 if _,e=os.Stat(path);!errors.Is(e,os.ErrNotExist){
  t.Fatalf("Defender owned sidecar not cleared after OS absence: %v",e)
 }
 t.Log("PLAN029_REAL_WINDOWS_DEFENDER_NATIVE_COM_EXACT_ADD_READBACK_CAS_DELETE_PASS_SCOPE_ONLY_NOT_PRODUCT_TCP")
}
