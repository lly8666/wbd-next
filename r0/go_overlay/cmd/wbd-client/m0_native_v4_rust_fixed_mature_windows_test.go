//go:build windows && wbd_v4_embedded_go
package main

import (
 "testing"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
)

func TestM0PLAN026WindowsFixedMatureProofNeverUsesConfiguredOrUnmaturedM2(t *testing.T){
 proof:=realityfront.V4WindowsFixedMatureReadback{
  Version:1,Size:56,Applied:1,Censored:0,
  CopiedSource:8,CopiedParity:4,ReverseReports:5,
  Positive2s:3,Covered2s:2,
 }
 if !m0WindowsFixedMatureVerified(proof){t.Fatal("original Rust authenticated positive M2 must be recognized")}
 negative:=[]struct{
  name string
  mutate func(*realityfront.V4WindowsFixedMatureReadback)
 }{
  {"unverified_version",func(p *realityfront.V4WindowsFixedMatureReadback){p.Version=0}},
  {"wrong_abi",func(p *realityfront.V4WindowsFixedMatureReadback){p.Size=0}},
  {"configured_without_applied",func(p *realityfront.V4WindowsFixedMatureReadback){p.Applied=0}},
  {"censored_capacity",func(p *realityfront.V4WindowsFixedMatureReadback){p.Censored=1}},
  {"no_actual_source",func(p *realityfront.V4WindowsFixedMatureReadback){p.CopiedSource=0}},
  {"no_actual_parity",func(p *realityfront.V4WindowsFixedMatureReadback){p.CopiedParity=0}},
  {"no_auth_reverse",func(p *realityfront.V4WindowsFixedMatureReadback){p.ReverseReports=0}},
  {"no_mature_positive",func(p *realityfront.V4WindowsFixedMatureReadback){p.Positive2s=0}},
  {"no_mature_coverage",func(p *realityfront.V4WindowsFixedMatureReadback){p.Covered2s=0}},
 }
 for _,tc:=range negative{t.Run(tc.name,func(t *testing.T){
  p:=proof;tc.mutate(&p)
  if m0WindowsFixedMatureVerified(p){t.Fatal("missing true source/M2/capacity gate must never claim Applied")}
 })}
}
