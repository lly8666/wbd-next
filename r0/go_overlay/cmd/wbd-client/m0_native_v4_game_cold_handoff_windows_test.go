//go:build windows && wbd_v4_embedded_go
package main
import (
 "net/netip"
 "path/filepath"
 "os"
 "testing"
 "errors"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
)
// Cold buffer exhaustion is not a reason to kill a genuine TLS reader,
// or cause a permanent Game4-FEC startup loss before native Rust handoff.
func TestM0PLAN027GameColdBacklogDropsOnlyOptionalDetachedM3(t *testing.T){
 inbound:=make(chan m0GameInbound,2)
 if !offerGameColdInbound(inbound,m0GameInbound{lane:0})||!offerGameColdInbound(inbound,m0GameInbound{lane:1}){t.Fatal("early capacity")}
 if offerGameColdInbound(inbound,m0GameInbound{lane:1}){t.Fatal("full buffer must not grow")}
 if len(inbound)!=2{t.Fatal("earlier authentic ciphertext replaced")}
 if (<-inbound).lane!=0{t.Fatal("FIFO cold ciphertext reordering")}
 if !offerGameColdInbound(inbound,m0GameInbound{lane:0}){t.Fatal("reader must resume after overflow")}
 if (<-inbound).lane!=1||(<-inbound).lane!=0{t.Fatal("later authentic M3 no longer admitted")}
}

func TestM0PLAN028GameAllLanesSameServerPortDifferentSources(t *testing.T){
 for _,serverPort:=range []uint16{443,8443}{
  o:=m0NativeV4Options{ServerIP:netip.MustParseAddr("192.0.2.19"),ServerPort:serverPort,SourcePort:41031}
  seen:=map[uint16]bool{}
  for lane:=0;lane<4;lane++{
   flow,err:=m0WindowsGameOriginalClientFlow(o,[4]byte{192,0,2,31},lane)
   if err!=nil{t.Fatalf("lane %d: %v",lane,err)}
   if flow.PeerPort!=serverPort{t.Fatalf("Game lane %d sent to %d, only %d is served",lane,flow.PeerPort,serverPort)}
   if flow.LocalPort!=uint16(41031+lane)||seen[flow.LocalPort]{t.Fatalf("Game lane %d local source collision",lane)}
   if flow.PeerIP!=o.ServerIP.As4(){t.Fatal("changed server IPv4")}
   seen[flow.LocalPort]=true
  }
 }
}
func TestM0PLAN028GameRejectSourcePortOverflowBeforeAnySYN(t *testing.T){
 o:=m0NativeV4Options{ServerIP:netip.MustParseAddr("192.0.2.19"),ServerPort:443,SourcePort:65535}
 if _,err:=m0WindowsGameOriginalClientFlow(o,[4]byte{192,0,2,31},1);err==nil{
  t.Fatal("Game4 source port wrap must fail before emitting first SYN")
 }
 o.SourcePort=41031;o.ServerPort=0
 if _,err:=m0WindowsGameOriginalClientFlow(o,[4]byte{192,0,2,31},0);err==nil{
  t.Fatal("missing fixed service port")
 }
}

// H2139: original 2/4 authenticated lanes share the SAME source-frozen
// Rust V4 cold policy and one owned Wintun. Verify no business OS rows
// in all/off, including an explicit all with the split checkbox set.
func TestM0PLAN029BGame2Game4BusinessSplitAllOffNoOSRows(t *testing.T){
 for _,mode:=range []m0WindowsV4Mode{m0WinModeGame2,m0WinModeGame4}{
  for _,tc:=range []struct{route string;enabled,want bool}{
   {"all",false,false},{"all",true,false},
   {"bypass-lan-cn",false,false},{"bypass-lan",true,true},
   {"bypass-lan-cn",true,true},
  }{
   o:=m0NativeV4Options{Mode:mode,RouteMode:tc.route,SplitEnable:tc.enabled}
   if got:=m0GameBusinessSplit(o);got!=tc.want{
    t.Fatalf("Game %s route=%s split=%t: OS business Direct=%t, want=%t",
     mode,tc.route,tc.enabled,got,tc.want)
   }
  }
 }
}

// The common 029B cold Rust constructor is mode-agnostic after the real
// TLS group epoch. This checks BOTH Game sizes, off/all/LAN/CN ordinary
// and advanced CN, including source-owned journal only for advanced.
func TestM0PLAN029BGame2Game4ThreeRouteModesColdV4(t *testing.T){
 physical:=netip.MustParseAddr("10.1.0.7")
 lease:=netip.MustParseAddr("10.234.12.34")
 for _,mode:=range []m0WindowsV4Mode{m0WinModeGame2,m0WinModeGame4}{
  for _,tc:=range []struct{route string;split,advanced bool;wantRoute,policy uint32}{
   {"all",false,false,0,0},{"all",true,true,0,0},
   {"bypass-lan-cn",false,true,0,0},
   {"bypass-lan",true,false,1,0},
   {"bypass-lan-cn",true,false,2,0},
   {"bypass-lan-cn",true,true,2,1},
  }{
   o:=plan029Options(tc.route);o.Mode=mode
   o.SplitEnable=tc.split;o.CNDomainDirect=tc.advanced
   o.StatePath=filepath.Join(t.TempDir(),"owned-wal")
   rules:=filepath.Join(t.TempDir(),"rules.txt")
   if err:=os.WriteFile(rules,[]byte("www.cn.example\n"),0600);err!=nil{t.Fatal(err)}
   o.CNRulesFile=rules
   t.Setenv("GITHUB_ACTIONS","false")
   t.Setenv("WBD_PLAN029_NATIVE_V3_TRIAL","")
   cold,err:=m0Plan029TrialCold(o,physical,14,lease,1389,[16]byte{2})
   if err!=nil||cold==nil||cold.RouteMode!=tc.wantRoute||
     cold.PolicyFlags!=tc.policy||cold.TCPSynthetic4==[4]byte{}{
    t.Fatalf("Game %s route=%s split=%t advanced=%t got=%+v err=%v",
     mode,tc.route,tc.split,tc.advanced,cold,err)
   }
   if tc.wantRoute==0&&(len(cold.Direct)>0||len(cold.CN)>0||
      len(cold.Domains)>0||len(cold.FakeJournalPath)>0){
    t.Fatalf("Game %s all/off allocated business resources",mode)
   }
   if tc.wantRoute==2&&len(cold.Domains)==0{
    t.Fatalf("Game %s CN missing exact DNS source",mode)
   }
   if (len(cold.FakeJournalPath)>0)!=(tc.policy==1){
    t.Fatalf("Game %s fake journal only for advanced CN",mode)
   }
  }
 }
}

// H2223 Windows parity: Game2/4 shares the same authenticated Rust
// activation contract as Normal. No user application packet is necessary
// before OS/WAL Applied and the independent product readiness receipt.
// The subsequent real UDP/TCP E2E scenarios still measure business delivery.
func TestH2223Game2Game4IdleNativeStartupDoesNotRequireApplicationReply(t *testing.T){
 for _,lanes:=range []int{2,4}{
  for _,row:=range []struct{tx,rx,after uint64}{
   {0,0,0},       // Completely idle genuine TLS/NPF/Wintun startup
   {27,0,0},      // Historical physical 27/0/0 startup failure
   {1,0,0},       // First packet copied, no peer response
   {12,8,4},      // Bidirectional business remains separate evidence
  }{
   v:=realityfront.V4WindowsNativeWorkerStatsV1{
    Version:1,Workers:2,TXCopied:row.tx,RXDelivered:row.rx,TXAfterRX:row.after,
   }
   if err:=m0WindowsRustNativeStartupVerdict(v);err!=nil{
    t.Fatalf("Game%d idle native activation %+v: %v",lanes,row,err)
   }
  }
 }
 for _,code:=range []int32{1,2,3,4,5,6,7}{
  v:=realityfront.V4WindowsNativeWorkerStatsV1{Version:1,Workers:2,WorkerError:code}
  if err:=m0WindowsRustNativeStartupVerdict(v);err==nil{
   t.Fatalf("Game native worker error %d must not become Ready",code)
  } else if code==6 && !errors.Is(err,errM0NativeV4AuthenticatedPeerDead){
   t.Fatalf("Game authenticated dead90 must retain reauth contract: %v",err)
  }
 }
}
