//! B5 cold-prepared CN8503 QNAME classifier used only at the ONE Android
//! Rust M4 IPv4/UDP53 TUN ingress. No Go/JNI per-packet callback, no FakeIP.
use regex::{RegexSet,RegexSetBuilder};
use std::collections::HashSet;

pub(crate) struct CNDnsMatcher{
    suffix:HashSet<String>,
    exact:HashSet<String>,
    regex:Option<RegexSet>,
    total:usize,
}
fn valid_domain(s:&str)->bool{
    !s.is_empty()&&s.len()<=253&&s.split('.').all(|part|
        !part.is_empty()&&part.len()<=63&&
        !part.starts_with('-')&&!part.ends_with('-')&&
        part.bytes().all(|b|b.is_ascii_lowercase()||b.is_ascii_digit()||b==b'-'))
}
impl CNDnsMatcher{
    /// These are the *same bytes* already pinned and parsed by original Go.
    /// All rule types are handled; no silent loss of three regexp patterns.
    pub(crate) fn from_go_cold(raw:&[u8])->Result<Self,()>{
        let text=std::str::from_utf8(raw).map_err(|_|())?;
        let mut suffix=HashSet::new();
        let mut exact=HashSet::new();
        let mut patterns=Vec::new();
        let mut total=0usize;
        for line in text.lines(){
            let (kind,value)=line.split_once(':').ok_or(())?;
            if value.is_empty()||value.len()>512{return Err(())}
            total+=1;
            match kind{
                "domain" if valid_domain(value)=>{
                    if !suffix.insert(value.to_owned()){return Err(())}
                },
                "full" if valid_domain(value)=>{
                    if !exact.insert(value.to_owned()){return Err(())}
                },
                "regexp"=>patterns.push(value.to_owned()),
                // The pinned original dataset contains zero keywords.
                // Reject a future format change rather than misclassify it.
                _=>return Err(()),
            }
        }
        let is_fixture=cfg!(test)&&total<100;
        if !is_fixture&&
           (total!=8503||suffix.len()!=8431||exact.len()!=69||patterns.len()!=3){
            return Err(())
        }
        let regex=if patterns.is_empty(){None}else{
            Some(RegexSetBuilder::new(patterns)
                .case_insensitive(true)
                .size_limit(16*1024*1024)
                .dfa_size_limit(16*1024*1024)
                .build().map_err(|_|())?)
        };
        Ok(Self{suffix,exact,regex,total})
    }
    pub(crate) fn total(&self)->usize{self.total}
    pub(crate) fn is_cn_name(&self,name:&str)->bool{
        if !valid_domain(name){return false}
        if self.exact.contains(name){return true}
        let mut suffix=name;
        loop{
            if self.suffix.contains(suffix){return true}
            let Some(dot)=suffix.find('.')else{break};
            suffix=&suffix[dot+1..];
        }
        self.regex.as_ref().is_some_and(|rx|rx.is_match(name))
    }
    /// Small ordinary IPv4/UDP53 (or already gathered jumbo) packet.
    /// The normal DNS ingress parser admitted the exact complete question.
    /// QNAME is decoded on the stack; no heap allocation per packet.
    pub(crate) fn is_cn_ipv4_query(&self,packet:&[u8])->bool{
        if packet.len()<45||packet[0]>>4!=4{return false}
        let ihl=usize::from(packet[0]&15)*4;
        if ihl<20||ihl>60||packet.len()<ihl+8+17||packet[9]!=17{return false}
        let start=ihl+8+12;
        let mut at=start;
        let mut name=[0u8;253];
        let mut used=0usize;
        let mut labels=0usize;
        loop{
            let Some(&n)=packet.get(at)else{return false};
            at+=1;
            if n==0{break}
            let n=usize::from(n);
            if n>63||at+n>packet.len()||labels>=127{return false}
            if labels>0{
                if used>=name.len(){return false}
                name[used]=b'.';used+=1;
            }
            if used+n>name.len(){return false}
            for &c in &packet[at..at+n]{
                let lower=c.to_ascii_lowercase();
                if !(lower.is_ascii_lowercase()||lower.is_ascii_digit()||lower==b'-'){
                    return false
                }
                name[used]=lower;
                used+=1;
            }
            at+=n;labels+=1;
        }
        if labels==0{return false}
        let Ok(s)=std::str::from_utf8(&name[..used])else{return false};
        self.is_cn_name(s)
    }
}
#[cfg(test)]
mod tests{
    use super::*;
    fn query(name:&str)->Vec<u8>{
        let mut dns=vec![0u8;12];dns[2]=1;dns[5]=1;
        for label in name.split('.'){
            dns.push(label.len() as u8);dns.extend_from_slice(label.as_bytes());
        }
        dns.extend_from_slice(&[0,0,1,0,1]);
        let n=28+dns.len();
        let mut ip=vec![0u8;n];
        ip[0]=0x45;ip[2..4].copy_from_slice(&(n as u16).to_be_bytes());
        ip[8]=64;ip[9]=17;ip[12..16].copy_from_slice(&[10,66,0,2]);
        ip[16..20].copy_from_slice(&[8,8,8,8]);
        ip[20..22].copy_from_slice(&45678u16.to_be_bytes());
        ip[22..24].copy_from_slice(&53u16.to_be_bytes());
        ip[24..26].copy_from_slice(&((n-20) as u16).to_be_bytes());
        ip[28..].copy_from_slice(&dns);ip
    }
    #[test]fn b5_cn8503_cold_match_domain_full_regex_and_no_false_suffix(){
        let raw=b"domain:baidu.com\nfull:only.example\nregexp:^ads[0-9]+[.]cn$\n";
        let m=CNDnsMatcher::from_go_cold(raw).unwrap();
        assert_eq!(m.total(),3);
        for q in ["baidu.com","www.baidu.com","only.example","ads123.cn"]{
            assert!(m.is_cn_ipv4_query(&query(q)), "{q} should be CN");
        }
        for q in ["notbaidu.com","only.example.net","ads.cn","www.example.net"]{
            assert!(!m.is_cn_ipv4_query(&query(q)), "{q} is not CN");
        }
    }
    #[test]fn b5_cn8503_cold_actual_pinned_rules_full_typed_when_supplied(){
        let Ok(path)=std::env::var("WBD_PINNED_CN_GEOSITE")else{return};
        let raw=std::fs::read(path).unwrap();
        let m=CNDnsMatcher::from_go_cold(&raw).unwrap();
        assert_eq!(m.total(),8503);
        for q in ["www.baidu.com","www.qq.com","baidu.com"]{
            assert!(m.is_cn_ipv4_query(&query(q)), "{q}");
        }
        for q in ["foo.example.cn","www.example.net","baidu.com.evil.example"]{
            assert!(!m.is_cn_ipv4_query(&query(q)), "{q}");
        }
    }
}
