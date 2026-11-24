package rootjournal

import(
 "errors"
 "os"
 "path/filepath"
 "testing"
)

func TestRestoreOwnedSingleRouteCrashAndIdempotence(t *testing.T){
 f,path,p:=fixture(t)
 s,e:=New(f.run,path,p)
 if e!=nil{t.Fatal(e)}
 if _,e=RecoverOwned(f.run,path);e==nil{t.Fatal("live owner lock stolen")}
 if e=s.lock.Close();e!=nil{t.Fatal(e)}
 recovered,e:=RecoverOwned(f.run,path)
 if e!=nil||!recovered||f.route||f.rule{t.Fatalf("not safely restored %v",e)}
 recovered,e=RecoverOwned(f.run,path)
 if e!=nil||recovered{t.Fatalf("idempotent clean Restore %v",e)}
}
func TestRestoreOwnedGroupAndAllApps(t *testing.T){
 t.Run("group",func(t *testing.T){
  f,path,p:=groupFixture(t)
  s,e:=NewGroup(f.run,path,p)
  if e!=nil{t.Fatal(e)}
  if e=s.lock.Close();e!=nil{t.Fatal(e)}
  restored,e:=RecoverOwned(f.run,path)
  if e!=nil||!restored||f.route||len(f.rules)!=0{t.Fatalf("group Restore %v",e)}
 })
 t.Run("all",func(t *testing.T){
  f,path,p:=allFixture(t)
  s,e:=NewAllApps(f.run,path,p)
  if e!=nil{t.Fatal(e)}
  if e=s.lock.Close();e!=nil{t.Fatal(e)}
  restored,e:=RecoverOwned(f.run,path)
  if e!=nil||!restored||f.route||f.peerThrow!=""||len(f.rules)!=0{
   t.Fatalf("all-app Restore %v",e)
  }
 })
}
func TestRestoreOwnedForeignStateAndJournalFailClosed(t *testing.T){
 for _,foreign:=range []string{"route","rule"}{
  t.Run(foreign,func(t *testing.T){
   f,path,_:=fixture(t)
   f.foreign=foreign
   if _,e:=RecoverOwned(f.run,path);e==nil{t.Fatal("foreign state treated as clean")}
   if len(f.calls)==0{t.Fatal("kernel readback not attempted")}
  })
 }
 f,path,_:=fixture(t)
 if e:=os.MkdirAll(filepath.Dir(path),0700);e!=nil{t.Fatal(e)}
 if e:=os.WriteFile(path,[]byte("malicious"),0600);e!=nil{t.Fatal(e)}
 if _,e:=RecoverOwned(f.run,path);e==nil{t.Fatal("forged journal accepted")}
 if _,e:=os.Stat(path);!errors.Is(e,nil){t.Fatal("journal unexpectedly deleted",e)}
}
func TestRestoreOwnedPartialJournalFailureRetained(t *testing.T){
 f,path,p:=groupFixture(t)
 s,e:=NewGroup(f.run,path,p)
 if e!=nil{t.Fatal(e)}
 s.lock.Close()
 f.failDelete=true
 if _,e=RecoverOwned(f.run,path);e==nil{t.Fatal("deleted only partial route")}
 if _,e=os.Stat(path);e!=nil{t.Fatal("lost partial rollback journal",e)}
}
