//go:build windows && wbd_v4_embedded_go
package main

import (
 "testing"
 "github.com/lly8666/wobuzhidao/internal/realityfront"
)

func TestM0PLAN026WindowsFixedMatureProofNeverUsesConfiguredOrUnmaturedM2(t *testing.T){
 proof:=realityfront.V4WindowsFixedMatureReadback{
  Version:1,Size:72,Applied:1,Censored:0,Profile:6,Revision:1,
  CopiedSource:8,CopiedParity:4,ReverseReports:5,
  Positive2s:3,Covered2s:2,
 }
 if !m0WindowsFixedMatureVerified(proof){t.Fatal("original Rust authenticated positive M2 must be recognized")}
 if !m0WindowsFixedInstalledVerified(proof,realityfront.FecV2Profile(6)){t.Fatal("real owner Fixed6 installed")}
 for _,mutate:=range []func(*realityfront.V4WindowsFixedMatureReadback){
  func(p *realityfront.V4WindowsFixedMatureReadback){p.CopiedSource=0;p.CopiedParity=0;p.Positive2s=0;p.Covered2s=0;p.Censored=1},
  func(p *realityfront.V4WindowsFixedMatureReadback){p.ReverseReports=0},
 }{
  p:=proof;mutate(&p)
  if !m0WindowsFixedInstalledVerified(p,realityfront.FecV2Profile(6)){
   t.Fatal("installed Fixed cannot wait for optional mature Quality")
  }
 }
 for _,tc:=range []struct{name string;mutate func(*realityfront.V4WindowsFixedMatureReadback)}{
  {"not_installed",func(p *realityfront.V4WindowsFixedMatureReadback){p.Applied=0}},
  {"wrong_profile",func(p *realityfront.V4WindowsFixedMatureReadback){p.Profile=5}},
  {"no_revision",func(p *realityfront.V4WindowsFixedMatureReadback){p.Revision=0}},
  {"wrong_abi",func(p *realityfront.V4WindowsFixedMatureReadback){p.Size=56}},
 }{
  t.Run("install_"+tc.name,func(t *testing.T){
   p:=proof;tc.mutate(&p)
   if m0WindowsFixedInstalledVerified(p,realityfront.FecV2Profile(6)){
    t.Fatal("uninstalled or mismatched Fixed cannot claim Applied")
   }
  })
 }
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
  if m0WindowsFixedMatureVerified(p){t.Fatal("missing true source/M2/capacity gate must never claim mature quality")}
 })}
}
