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
