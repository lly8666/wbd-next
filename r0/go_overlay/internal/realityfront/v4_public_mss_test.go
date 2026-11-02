package realityfront
import "github.com/lly8666/wobuzhidao/internal/faketcp"
// Only original-Go realityfront tests: production V4 MSS is Rust cold-derived.
func init(){if err:=faketcp.SetPublicV4AdvertisedMSS(1420);err!=nil{panic(err)}}
