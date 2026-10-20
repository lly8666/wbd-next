//go:build linux && cgo && wbd_v4_embedded_go
package main
import (
 "log"
 "os"
 "github.com/lly8666/wobuzhidao/internal/v4productcli"
)
func main(){if err:=v4productcli.Run("server",os.Args[1:]);err!=nil{log.Fatal(err)}}
