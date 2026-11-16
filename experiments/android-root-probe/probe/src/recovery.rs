//! Explicit user-triggered recovery of ONLY the older WBD AVD probe's exact rule.
//! Never flush Android netd, change global defaults, kill unknown workers or touch
//! production Wi-Fi/USB interfaces. No state change without a narrow positive match.
use serde_json::{json,Value};
use std::process::Command;
use std::io;
use std::time::{Duration,Instant};
use std::thread;

const PREFIX:&str="198.18.254.2";
const TABLE:&str="235";
fn ip(args:&[&str])->io::Result<String>{
    let mut p=Command::new("ip").args(args).spawn()?;
    let deadline=Instant::now()+Duration::from_secs(3);
    loop{
        if let Some(status)=p.try_wait()?{
            // For commands whose stdout is needed, use output() in list below.
            return if status.success(){Ok(String::new())}else{
                Err(io::Error::other(format!("ip {args:?} status {status}")))
            }
        }
        if Instant::now()>=deadline{
            let _=p.kill();let _=p.wait();
            return Err(io::Error::new(io::ErrorKind::TimedOut,"ip command >3s"))
        }
        thread::sleep(Duration::from_millis(25));
    }
}
fn list(args:&[&str])->io::Result<String>{
    let o=Command::new("ip").args(args).output()?;
    if !o.status.success(){return Err(io::Error::other(format!("ip {args:?}: {}",String::from_utf8_lossy(&o.stderr))))}
    Ok(String::from_utf8_lossy(&o.stdout).into_owned())
}
fn state(uid:u32)->Value{
    let result=(||->io::Result<Value>{
        let rules=list(&["-4","rule","show"])?;
        let routes=list(&["-4","route","show","table",TABLE])?;
        let ours=format!("uidrange {uid}-{uid}");
        let candidates:Vec<&str>=rules.lines().filter(|l|l.trim_start().starts_with("8200:")).collect();
        let exact=candidates.len()==1 &&
            candidates[0].contains(&ours) &&
            candidates[0].contains("to 198.18.254.2") &&
            (candidates[0].contains("lookup 235")||candidates[0].contains("lookup 0xeb"));
        let other_lookup=rules.lines().any(|l|!l.trim_start().starts_with("8200:") &&
            (l.contains("lookup 235")||l.contains("lookup 0xeb")));
        let route_lines:Vec<&str>=routes.lines().filter(|s|!s.trim().is_empty()).collect();
        let route_dev=if route_lines.len()==1 {
            let cols:Vec<&str>=route_lines[0].split_ascii_whitespace().collect();
            let idx=cols.iter().position(|s|*s=="dev");
            if cols.first().is_some_and(|x|x.starts_with(PREFIX)) {
                idx.and_then(|i|cols.get(i+1)).copied()
            }else{None}
        }else{None};
        let route_owned=route_dev.is_some_and(|d|
            d.starts_with("wba") && d.len()<=15 &&
            d[3..].bytes().all(|x|x.is_ascii_hexdigit()));
        let collision=(!candidates.is_empty()&&!exact)||other_lookup||
            (!route_lines.is_empty()&&!route_owned);
        Ok(json!({"rules":rules,"routes":routes,"exact_rule":exact,
            "rule_count_at_priority":candidates.len(),"other_lookup235":other_lookup,
            "route_dev":route_dev,"route_owned":route_owned,"collision":collision}))
    })();
    match result{
        Ok(v)=>v,Err(e)=>json!({"error":e.to_string(),"status":"FAIL"})
    }
}
fn guard(uid:u32)->Option<Value>{
    if unsafe{libc::geteuid()}!=0 || uid<10000||uid>199999{
        return Some(json!({"status":"PERMISSION_DENIED","reason":"root and ordinary app UID required","uid":uid}))
    }
    let gp=Command::new("getprop").arg("ro.kernel.qemu").output().ok()
        .map(|v|String::from_utf8_lossy(&v.stdout).trim().to_owned()).unwrap_or_default();
    if gp!="1"{
        return Some(json!({"status":"ENV_BLOCKED","reason":"probe recovery restricted to disposable emulator; physical device needs durable journal","uid":uid}))
    }
    None
}
pub fn seed(uid:u32)->Value{
    if let Some(v)=guard(uid){return v}
    let before=state(uid);
    if before.get("error").is_some(){return before}
    if before["collision"]==true||before["exact_rule"]==true||
        before["routes"].as_str().is_some_and(|x|!x.trim().is_empty()){
        return json!({"status":"ENV_BLOCKED","reason":"existing priority/table; refusing synthetic seed","before":before})
    }
    let range=format!("{uid}-{uid}");
    match ip(&["-4","rule","add","pref","8200","uidrange",&range,"to","198.18.254.2/32","lookup",TABLE]){
        Err(e)=>json!({"status":"FAIL","reason":e.to_string(),"before":before}),
        Ok(_)=>{
            let after=state(uid);
            json!({"status":if after["exact_rule"]==true{"FIXTURE_SEEDED"}else{"FAIL"},
                "before_rule":before["rules"],"after":after,
                "scope":"synthetic orphaned WBD UID-specific /32 rule; no route or netfilter change"})
        }
    }
}
pub fn restore(uid:u32)->Value{
    if let Some(v)=guard(uid){return v}
    let before=state(uid);
    if before.get("error").is_some(){return before}
    if before["collision"]==true{
        return json!({"status":"REFUSED_AMBIGUOUS","reason":"non-owned priority8200 or table235 entry; no changes","before":before})
    }
    if before["exact_rule"]!=true &&
        before["routes"].as_str().is_some_and(|x|x.trim().is_empty()){
        return json!({"status":"ALREADY_CLEAN","uid":uid,"root_uid":unsafe{libc::geteuid()},
            "global_changes":false,"before":before})
    }
    // An interface still alive can be owned by a running worker. Refuse to
    // remove its routing without first stopping its lease, even if name matches.
    if let Some(dev)=before["route_dev"].as_str(){
        if list(&["link","show","dev",dev]).is_ok(){
            return json!({"status":"REFUSED_ACTIVE_WORKER","uid":uid,"dev":dev,"before":before})
        }
    }
    let range=format!("{uid}-{uid}");
    let mut errors=Vec::new();
    if before["exact_rule"]==true {
        if let Err(e)=ip(&["-4","rule","del","pref","8200","uidrange",&range,
                          "to","198.18.254.2/32","lookup",TABLE]){errors.push(e.to_string())}
    }
    if before["route_owned"]==true {
        if let Err(e)=ip(&["-4","route","del","198.18.254.2/32",
                          "table",TABLE]){errors.push(e.to_string())}
    }
    let after=state(uid);
    // All other policy rules are stable; no flush and no default-route mutation.
    let filtered=|v:&Value| -> Vec<String>{
        v["rules"].as_str().unwrap_or("").lines()
            .filter(|l|!l.trim_start().starts_with("8200:"))
            .map(str::to_owned).collect()
    };
    let other_rules_equal=filtered(&before)==filtered(&after);
    let clean=after["exact_rule"]==false &&
        after["rules"].as_str().is_some_and(|s|!s.lines().any(|l|l.trim_start().starts_with("8200:"))) &&
        after["routes"].as_str().is_some_and(|s|s.trim().is_empty()) &&
        after["collision"]==false && other_rules_equal;
    json!({"schema":"wbd-owned-network-recover/v1","status":
        if clean&&errors.is_empty(){"RESTORED"}else{"FAIL"},
        "uid":uid,"root_uid":unsafe{libc::geteuid()},
        "before":before,"after":after,"other_rules_equal":other_rules_equal,
        "errors":errors,"scope":"only priority8200 UID-specific 198.18.254.2/32 table235 orphan; no production recovery"})
}
#[cfg(test)]
mod tests{
 use super::*;
 #[test] fn guard_rejects_non_app_uid(){assert_eq!(guard(9999).unwrap()["status"],"PERMISSION_DENIED");}
}
