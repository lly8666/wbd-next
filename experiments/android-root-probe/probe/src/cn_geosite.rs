//! Cold CN geosite DNS matcher. This is **not** a route implementation.
//! Imported domain/full/keyword/regexp semantics are independent from
//! Android real-IP data admission and from the Windows selective FakeIP.
//! DNS interception and production WBD control/TLS are NOT_RUN.
use regex::{RegexSet,RegexSetBuilder};
use serde_json::{json,Value};
use sha2::{Digest,Sha256};
use std::collections::HashSet;
use std::fs;
use std::path::Path;

pub(crate) struct Index {
    suffix:HashSet<String>,
    exact:HashSet<String>,
    keywords:Vec<String>,
    regexes:Option<RegexSet>,
    count:usize,
    sha256:String,
}
fn domain(name:&str)->Result<String,String>{
    let n=name.trim_end_matches('.').to_ascii_lowercase();
    if n.is_empty()||n.len()>253||!n.is_ascii(){
        return Err("non-ASCII/IDNA or empty DNS name (caller must punycode)".into())
    }
    if n.split('.').any(|l|l.is_empty()||l.len()>63||l.starts_with('-')||
        l.ends_with('-')||!l.bytes().all(|b|b.is_ascii_alphanumeric()||b==b'-')){
        return Err(format!("invalid DNS label in {n}"))
    }
    Ok(n)
}
fn valid_hash(expected:&str)->bool{
    expected.len()==64 && expected.bytes().all(|c|c.is_ascii_hexdigit())
}
impl Index {
    pub(crate) fn load(path:&Path,expected_sha256:&str)->Result<Self,String>{
        if !valid_hash(expected_sha256){
            return Err("missing/malformed pinned CN geosite SHA256".into())
        }
        let meta=fs::metadata(path).map_err(|e|format!("CN geosite unavailable: {e}"))?;
        if !(10_000..6_000_000).contains(&meta.len()){
            return Err(format!("CN geosite invalid file bytes={}",meta.len()))
        }
        let b=fs::read(path).map_err(|e|e.to_string())?;
        let digest=format!("{:x}",Sha256::digest(&b));
        if !digest.eq_ignore_ascii_case(expected_sha256){
            return Err("CN geosite content digest changed: FAIL_CLOSED".into())
        }
        let txt=std::str::from_utf8(&b).map_err(|e|e.to_string())?;
        let mut suffix=HashSet::new();
        let mut exact=HashSet::new();
        let mut keywords=HashSet::new();
        let mut patterns=Vec::new();
        let mut count=0usize;
        for (i,line) in txt.lines().enumerate(){
            if line.is_empty(){continue}
            count+=1;
            if count>150_000{return Err("too many geosite rules".into())}
            let (kind,payload)=line.split_once(':')
                .ok_or_else(||format!("line {}: missing rule kind",i+1))?;
            if payload.is_empty()||payload.len()>512{
                return Err(format!("line {}: invalid rule size",i+1))
            }
            match kind{
                "domain"=>{suffix.insert(domain(payload)?);},
                "full"=>{exact.insert(domain(payload)?);},
                "keyword"=>{
                    let lower=payload.to_ascii_lowercase();
                    if !lower.is_ascii()||!lower.bytes().all(|c|c.is_ascii_alphanumeric()||c==b'.'||c==b'-'){
                        return Err(format!("invalid keyword line {}",i+1))
                    }
                    keywords.insert(lower);
                },
                "regexp"=>{patterns.push(payload.to_owned());},
                _=>return Err(format!("unsupported imported geosite kind line {}",i+1))
            }
        }
        if count<1000||suffix.len()<1000{
            return Err(format!("geosite is suspiciously incomplete: total={count} suffix={}",suffix.len()))
        }
        if keywords.len()>8192||patterns.len()>2048{
            return Err("oversized geosite keyword/regexp rule set".into())
        }
        let regexes=if patterns.is_empty(){None}else{
            Some(RegexSetBuilder::new(&patterns)
                .case_insensitive(true)
                .size_limit(16*1024*1024)
                .dfa_size_limit(16*1024*1024)
                .build().map_err(|e|format!("unsupported source Go regexp in Rust matcher, cannot silently ignore: {e}"))?)
        };
        let mut kws=keywords.into_iter().collect::<Vec<_>>();
        kws.sort_unstable();
        Ok(Self{suffix,exact,keywords:kws,regexes,count,sha256:digest})
    }
    pub(crate) fn has(&self,name:&str)->Result<bool,String>{
        let q=domain(name)?;
        if self.exact.contains(&q){return Ok(true)}
        for (i,part) in q.match_indices('.'){
            let _=part;
            if self.suffix.contains(&q[i+1..]){return Ok(true)}
        }
        if self.suffix.contains(&q){return Ok(true)}
        if self.keywords.iter().any(|w|q.contains(w)){return Ok(true)}
        Ok(self.regexes.as_ref().map(|r|r.is_match(&q)).unwrap_or(false))
    }
    pub(crate) fn evidence(&self)->Value{
        json!({"sha256":self.sha256,"total_rules":self.count,
            "suffixes":self.suffix.len(),"exact":self.exact.len(),
            "keyword":self.keywords.len(),
            "regexp":self.regexes.as_ref().map(|r|r.len()).unwrap_or(0),
            "matching_only_at_dns_admission":true,
            "data_egress_uses_resolved_ip":true})
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    #[test]fn invalid_domain_rejected(){
        assert!(domain("a..cn").is_err());
        assert_eq!(domain("BaIDU.COM."),Ok("baidu.com".into()));
        assert!(domain("a.example.cn").is_ok());
    }
}
