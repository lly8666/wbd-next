package runtimeentry

import(
 "flag"
 "testing"
)
func TestM0PLAN026NativeHealthSeparateIntervalDeadAndOptionalDormant(t *testing.T){
 fs:=flag.NewFlagSet("health",flag.ContinueOnError)
 p:=RegisterFEC2ProductFlags(fs)
 if err:=p.Validate(1);err!=nil{t.Fatal(err)}
 if *p.HealthKeepaliveSeconds!=15||*p.HealthDeadAfterSeconds!=90||
    *p.HealthIdleDormantSeconds!=0{
  t.Fatal("original user defaults 15s/90s and no dormant")
 }
 if err:=fs.Set("health.keepalive_seconds","30");err!=nil{t.Fatal(err)}
 if err:=fs.Set("health.dead_after_seconds","90");err!=nil{t.Fatal(err)}
 if err:=fs.Set("health.idle_dormant_seconds","60");err!=nil{t.Fatal(err)}
 if err:=p.Validate(1);err!=nil{t.Fatal(err)}
 if err:=fs.Set("health.dead_after_seconds","89");err!=nil{t.Fatal(err)}
 if err:=p.Validate(1);err==nil{t.Fatal("dead-after must be >=3x actual keepalive")}
 if err:=fs.Set("health.dead_after_seconds","90");err!=nil{t.Fatal(err)}
 if err:=fs.Set("health.keepalive_seconds","0");err!=nil{t.Fatal(err)}
 if err:=p.Validate(1);err==nil{t.Fatal("zero heartbeat invalid")}
}
