//go:build windows

package main

import (
 "context"
 "errors"
 "os"
 "strings"
 "testing"

 "github.com/lly8666/wobuzhidao/internal/windowsclient"
)

// The historical PowerShell Apply/Cleanup tests cannot be carried forward
// unchanged after removing networkCommandContext/applyOwnedNetworkWith.
// These tests enforce the new native-only fail-closed boundary instead.
func TestN4NativeApplyNeverFallsBackToPowerShell(t *testing.T) {
 for i:=0;i<2;i++ {
  cleanup,err:=applyOwnedNetwork(context.Background(),windowsclient.NetworkPlan{})
  if cleanup!=nil || !errors.Is(err,windowsclient.ErrN4NativeGuard) {
   t.Fatalf("unqualified native Apply claimed success on attempt %d: %v",i,err)
  }
 }
}
func TestN4NativeCanceledApplyMustNotReportSuccess(t *testing.T) {
 ctx,cancel:=context.WithCancel(context.Background());cancel()
 cleanup,err:=applyOwnedNetwork(ctx,windowsclient.NetworkPlan{})
 if cleanup!=nil || !errors.Is(err,context.Canceled) {
  t.Fatalf("canceled Apply promoted to success: cleanup=%v err=%v",cleanup!=nil,err)
 }
}
func TestN4NativeNetworkOwnerUnqualifiedMustReject(t *testing.T) {
 err:=windowsclient.N4NativeNetworkReady(context.Background())
 if !errors.Is(err,windowsclient.ErrN4NativeGuard) {
  t.Fatalf("unsafe native WFP owner was enabled: %v",err)
 }
}
func TestN4NativeRuntimeHasNoOldScriptCommandLauncher(t *testing.T) {
 raw,err:=os.ReadFile("main_windows.go")
 if err!=nil{t.Fatal(err)}
 src:=string(raw)
 for _,forbidden:=range []string{"powershell.exe","exec.CommandContext","networkCommandContext","applyOwnedNetworkWith","windows_client_network.ps1"} {
  if strings.Contains(src,forbidden){t.Fatalf("original Windows production entry still contains retired launcher: %s",forbidden)}
 }
}
