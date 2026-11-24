package rootjournal

import "strings"

// Read-only selected UID kernel route-get witness; does not model Android
// socket fwmarks, netd resolver or a Chrome data packet.
func SelectedUIDRouteGetUsesTun(out,tun string)bool{
 if !nameOK(tun){return false}
 lines:=strings.Split(strings.TrimSpace(out),"\n")
 fields:=strings.Fields(lines[0])
 if len(fields)<3{return false}
 for _,w:=range fields{
  switch w{case "unreachable","throw","blackhole","prohibit":return false}
 }
 for i:=0;i+1<len(fields);i++{
  if fields[i]=="dev"{return fields[i+1]==tun}
 }
 return false
}
