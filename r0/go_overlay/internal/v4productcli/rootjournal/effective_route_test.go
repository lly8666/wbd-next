package rootjournal

import "testing"

func TestA44OriginalUIDEffectiveRouteGetParser(t *testing.T){
 for _,tc:=range []struct{out string;want bool}{
  {"1.1.1.1 dev wbdtun0 src 10.66.0.2 uid 10234\n cache\n",true},
  {"1.1.1.1 via 192.0.2.1 dev wlan0 src 192.0.2.2 uid 10234",false},
  {"unreachable 1.1.1.1 dev wbdtun0 uid 10234",false},
  {"throw 1.1.1.1 dev wbdtun0 uid 10234",false},
  {"1.1.1.1 dev wbdtun00 uid 10234",false},
  {"1.1.1.1 uid 10234",false},
  {"",false},
 }{
  if got:=SelectedUIDRouteGetUsesTun(tc.out,"wbdtun0");got!=tc.want{
   t.Fatalf("kernel route-get %q: got %t want %t",tc.out,got,tc.want)
  }
 }
}
