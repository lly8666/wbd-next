//go:build windows
package main

import "testing"

func TestM0PLAN023WindowsNativeV4FiveModes(t *testing.T){
 cases:=[]struct{lanes int;fec2 string;want m0WindowsV4Mode}{
  {1,"off",m0WinModeNormal},
  {1,"fixed",m0WinModeFixed},
  {1,"auto",m0WinModeAuto},
  {2,"off",m0WinModeGame2},
  {4,"off",m0WinModeGame4},
 }
 for _,tc:=range cases{
  got,err:=m0ParseWindowsV4Mode(tc.lanes,tc.fec2,"legacy",0)
  if err!=nil||got!=tc.want{t.Errorf("lanes=%d mode=%s got=%s err=%v",tc.lanes,tc.fec2,got,err)}
 }
 invalid:=[]struct{lanes int;fec2,legacy string;parity int}{
  {3,"off","legacy",0},
  {2,"fixed","legacy",0},
  {4,"auto","legacy",0},
  {1,"off","auto",0},
  {1,"off","legacy",4},
  {1,"bad","legacy",0},
 }
 for _,tc:=range invalid{
  if got,err:=m0ParseWindowsV4Mode(tc.lanes,tc.fec2,tc.legacy,tc.parity);err==nil{
   t.Errorf("invalid mode incorrectly accepted: %s",got)
  }
 }
}
