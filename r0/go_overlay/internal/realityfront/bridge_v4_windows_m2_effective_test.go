//go:build windows && wbd_v4_embedded_go
package realityfront
import(
 "testing"
 "unsafe"
)
func TestM0WindowsEffectiveM2ABISize(t *testing.T){
 var value V4WindowsM2Effective
 if unsafe.Sizeof(value)!=72{t.Fatalf("C ABI M2 effective size=%d",unsafe.Sizeof(value))}
 // A cold zero-value struct cannot be mislabeled as a readback receipt.
 if value.Version!=0||value.V3Enabled!=0{t.Fatal("unverified effective defaults")}
}

func TestM0WindowsOriginalM2BatchFirstsendABIExactCLayout(t *testing.T){
 var row V4WindowsM2FirstsendResult
 if unsafe.Sizeof(row)!=24 || unsafe.Offsetof(row.PN)!=0 ||
   unsafe.Offsetof(row.Seq)!=8 || unsafe.Offsetof(row.WireLen)!=12 ||
   unsafe.Offsetof(row.Outcome)!=16 || unsafe.Offsetof(row.Reserved)!=20 {
  t.Fatalf("original-NPF batch C ABI mismatch; size=%d",unsafe.Sizeof(row))
 }
 if V4WindowsM2FirstsendBatchMax!=32{
  t.Fatal("unbounded original M2 batch")
 }
}
