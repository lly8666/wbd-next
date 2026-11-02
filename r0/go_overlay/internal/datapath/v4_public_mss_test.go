package datapath
import "github.com/lly8666/wobuzhidao/internal/faketcp"
// Bounded pre-existing Go pathmtu tests ONLY: production has no default MSS.
func init(){if err:=faketcp.SetPublicV4AdvertisedMSS(1420);err!=nil{panic(err)}}
