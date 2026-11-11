package realityfront
import("testing")
func TestPLAN028ServerAccountBoundManualLeaseOnlyAfterAuth(t *testing.T){
 by:=map[string]string{"alice":"10.66.0.2/32","bob":"10.66.0.3/32"}
 for _,tc:=range []struct{user string;auto bool;want string}{
  {"alice",false,"10.66.0.2/32"},{"bob",false,"10.66.0.3/32"},{"alice",true,"10.66.0.2/32"},{"bob",true,"10.66.0.3/32"},{"mallory",false,""},{"mallory",true,""},
 }{
  got,err:=v4ServerSelectedManualLease4("",by,tc.user,tc.auto)
  if tc.want==""{if err==nil{t.Fatalf("unauthorized manual lease: %+v = %q",tc,got)}}else if err!=nil||got!=tc.want{t.Fatalf("bound account %+v got=%q err=%v",tc,got,err)}
 }
 if _,err:=v4ServerSelectedManualLease4("10.66.0.9/32",by,"alice",false);err==nil{t.Fatal("global manual & per-account conflict")}
 if _,err:=v4ServerSelectedManualLease4("10.66.0.9/32",by,"alice",true);err==nil{t.Fatal("auto must not escape global+roster conflict")}
 if _,err:=v4ServerSelectedManualLease4("10.66.0.9/32",nil,"alice",true);err==nil{t.Fatal("legacy singleton manual auto forbidden")}
 if _,err:=v4ServerSelectedManualLease4("",nil,"alice",false);err!=nil{t.Fatal(err)}
 if got,err:=v4ServerSelectedManualLease4("10.66.0.9/32",nil,"alice",false);err!=nil||got!="10.66.0.9/32"{t.Fatalf("legacy explicit lease changed: %q %v",got,err)}
}
