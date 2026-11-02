//go:build windows && wbd_v4_embedded_go
package windowsownerlease
import "github.com/lly8666/wobuzhidao/internal/faketcp"
// PLAN020-only signed TLS test source. Never copy into frozen-M4 ABI tests.
// Production calls Rust physical-outer cold budget before new association.
func init(){if err:=faketcp.SetPublicV4AdvertisedMSS(1420);err!=nil{panic(err)}}
