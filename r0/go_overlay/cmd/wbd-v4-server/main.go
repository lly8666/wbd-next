//go:build linux && cgo && wbd_v4_embedded_go
package main
import (
 "log"
 "os"
 "github.com/lly8666/wobuzhidao/internal/v4productcli"
)
func main(){args:=os.Args[1:];var err error;if len(args)>0&&args[0]=="--manage"{err=v4productcli.ManageServer(args[1:])}else{err=v4productcli.Run("server",args)};if err!=nil{log.Fatal(err)}}
