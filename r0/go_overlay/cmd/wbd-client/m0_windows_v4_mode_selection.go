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
 // Match the verified Linux original-Go V3 carrier admission *before*
 // the native V4 dispatch: Fixed must retain fixed4 in the original
 // bootstrap policy while Rust FEC2 FixedStream independently owns
 // the Maximum6 source/repair matrix after authenticated Detach.
 // This is a two-namespace contract, not a second Go steady FEC owner.
 if lanes==1&&fec2=="fixed"{
  if legacy!="fixed"||parity!=4 {
   return "",fmt.Errorf("V4 Fixed6 requires original Go V3 carrier fixed parity4 admission")
  }
  return m0WinModeFixed,nil
 }
 if parity!=0||(legacy!="legacy"&&legacy!="off") {
  return "",fmt.Errorf("V4 native mode cannot mix with legacy FEC")
 }
 switch lanes {
 case 1:
  switch fec2 {
  case "off":return m0WinModeNormal,nil
  case "auto":return m0WinModeAuto,nil
  }
 case 2:
  if fec2=="off" {return m0WinModeGame2,nil}
 case 4:
  if fec2=="off" {return m0WinModeGame4,nil}
 }
 return "",fmt.Errorf("unsupported native V4 lanes=%d fec2=%s",lanes,fec2)
}
