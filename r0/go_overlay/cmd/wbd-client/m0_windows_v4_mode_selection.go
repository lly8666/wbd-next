//go:build windows
package main

import "fmt"

type m0WindowsV4Mode string

const (
 m0WinModeNormal m0WindowsV4Mode = "normal"
 m0WinModeFixed m0WindowsV4Mode = "fec-fixed"
 m0WinModeAuto m0WindowsV4Mode = "fec-auto"
 m0WinModeGame2 m0WindowsV4Mode = "game2"
 m0WinModeGame4 m0WindowsV4Mode = "game4"
)

func m0ParseWindowsV4Mode(lanes int,fec2,legacy string,parity int)(m0WindowsV4Mode,error){
 if parity!=0||(legacy!="legacy"&&legacy!="off") {
  return "",fmt.Errorf("V4 native mode cannot mix with legacy FEC")
 }
 switch lanes {
 case 1:
  switch fec2 {
  case "off":return m0WinModeNormal,nil
  case "fixed":return m0WinModeFixed,nil
  case "auto":return m0WinModeAuto,nil
  }
 case 2:
  if fec2=="off" {return m0WinModeGame2,nil}
 case 4:
  if fec2=="off" {return m0WinModeGame4,nil}
 }
 return "",fmt.Errorf("unsupported native V4 lanes=%d fec2=%s",lanes,fec2)
}
