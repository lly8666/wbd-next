//go:build windows && wbd_v4_embedded_go
package realityfront
import ("testing";"unsafe")

// Compare independent Rust repr(C) cold ABI: not just the total size.
func TestPlan029V3ExactColdABIAndNegativeLimits(t *testing.T){
 if unsafe.Sizeof(V4WindowsColdCIDR{})!=8 ||
  unsafe.Sizeof(v4WindowsColdSplitWireV1{})!=120 ||
  unsafe.Offsetof(v4WindowsColdSplitWireV1{}.CN)!=64 ||
  unsafe.Offsetof(v4WindowsColdSplitWireV1{}.Domains)!=96 ||
  unsafe.Offsetof(v4WindowsColdSplitWireV1{}.JournalPath)!=112{
  t.Fatalf("V3 ABI mismatch: row=%d split=%d",
   unsafe.Sizeof(V4WindowsColdCIDR{}),
   unsafe.Sizeof(v4WindowsColdSplitWireV1{}))
 }
 c:=V4WindowsColdSplitConfig{RouteMode:2,PhysicalIfIndex:14,
  InnerMTU:1280,DirectHard:16384,
  CN:[]V4WindowsColdCIDR{{Network:[4]byte{203,0,113,0},Bits:24}},
  Domains:[]byte("cn.example\n")}
 w,e:=c.wire()
 if e!=nil||w.Size!=120||w.CNCount!=1||w.CN==0||
  w.DomainsLength!=11||w.Domains==0{
  t.Fatalf("invalid C cold readback: %+v err=%v",w,e)
 }
 c.DirectHard=16385
 if _,e:=c.wire();e==nil{t.Fatal("unbounded hard quota")}
 c.DirectHard=16384;c.RouteMode=3
 if _,e:=c.wire();e==nil{t.Fatal("unknown mode")}
 c.RouteMode=2;c.InnerMTU=100
 if _,e:=c.wire();e==nil{t.Fatal("invalid native inner MTU")}
}
